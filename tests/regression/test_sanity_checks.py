import pytest
from brownie import web3, reverts, accounts, chain  # type: ignore
from utils.test.exit_bus_data import LidoValidator
from utils.test.extra_data import ExtraDataService
from utils.test.oracle_report_helpers import (
    oracle_report,
    prepare_exit_bus_report,
    reach_consensus,
    wait_to_next_available_report_time,
)
from utils.evm_script import encode_error

from utils.test.helpers import ETH, GWEI, eth_balance
from utils.config import (
    contracts,
    CHURN_VALIDATORS_PER_DAY_LIMIT,
    ONE_OFF_CL_BALANCE_DECREASE_BP_LIMIT,
    ANNUAL_BALANCE_INCREASE_BP_LIMIT,
    MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT,
    MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT,
    MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT,
    REQUEST_TIMESTAMP_MARGIN,
)

ONE_DAY = 1 * 24 * 60 * 60
ONE_YEAR = 365 * ONE_DAY
MAX_BASIS_POINTS = 10000


@pytest.fixture(scope="module")
def eth_whale(accounts):
    return accounts.at("0x00000000219ab540356cBB839Cbe05303d7705Fa", force=True)


@pytest.fixture(scope="module")
def pre_cl_balance():
    (_, _, pre_cl_balance) = contracts.lido.getBeaconStat()
    return pre_cl_balance


@pytest.fixture(scope="module", autouse=True)
def first_report():
    oracle_report(silent=True)


@pytest.fixture()
def extra_data_service():
    return ExtraDataService()


def test_cant_report_more_validators_than_deposited():
    with reverts("REPORTED_MORE_DEPOSITED"):
        oracle_report(cl_diff=ETH(100), cl_appeared_validators=1000, skip_withdrawals=True, silent=True)


def test_validators_cant_decrease():
    with reverts("REPORTED_LESS_VALIDATORS"):
        oracle_report(cl_diff=ETH(100), cl_appeared_validators=-1, skip_withdrawals=True, silent=True)


def test_too_large_cl_increase(pre_cl_balance):
    #   uint256 annualBalanceIncrease = ((365 days * MAX_BASIS_POINTS * balanceIncrease) /
    #         _preCLBalance) /
    #         _timeElapsed;
    max_balance_increase = ANNUAL_BALANCE_INCREASE_BP_LIMIT * ONE_DAY * pre_cl_balance // ONE_YEAR // MAX_BASIS_POINTS

    error_balance_increase = max_balance_increase + ETH(100)
    error_annual_balance_increase = (ONE_YEAR * MAX_BASIS_POINTS * error_balance_increase) // pre_cl_balance // ONE_DAY
    with reverts(encode_error("IncorrectCLBalanceIncrease(uint256)", [error_annual_balance_increase])):
        oracle_report(cl_diff=error_balance_increase, skip_withdrawals=True, silent=True)


def test_too_large_cl_increase_with_appeared_validator(pre_cl_balance):
    max_balance_increase = ANNUAL_BALANCE_INCREASE_BP_LIMIT * ONE_DAY * pre_cl_balance // ONE_YEAR // MAX_BASIS_POINTS
    error_balance_increase = max_balance_increase + ETH(100)
    error_annual_balance_increase = (ONE_YEAR * MAX_BASIS_POINTS * error_balance_increase) // pre_cl_balance // ONE_DAY

    with_appeared_validator = error_balance_increase + ETH(32)
    fake_deposited_validators_increase(1)

    with reverts(encode_error("IncorrectCLBalanceIncrease(uint256)", [error_annual_balance_increase])):
        oracle_report(cl_diff=with_appeared_validator, cl_appeared_validators=1, skip_withdrawals=True, silent=True)


def test_too_much_validators_appeared():
    deposited_validators = CHURN_VALIDATORS_PER_DAY_LIMIT + 1
    fake_deposited_validators_increase(deposited_validators)

    with reverts(encode_error("IncorrectAppearedValidators(uint256)", [deposited_validators])):
        oracle_report(
            cl_diff=ETH(32) * deposited_validators,
            cl_appeared_validators=deposited_validators,
            skip_withdrawals=True,
            silent=True,
        )


def test_too_much_validators_exited():
    with reverts(
        encode_error(
            "ExitedValidatorsLimitExceeded(uint256,uint256)",
            [CHURN_VALIDATORS_PER_DAY_LIMIT, CHURN_VALIDATORS_PER_DAY_LIMIT + 1],
        )
    ):
        oracle_report(
            numExitedValidatorsByStakingModule=[CHURN_VALIDATORS_PER_DAY_LIMIT + 1],
            stakingModuleIdsWithNewlyExitedValidators=[1],
            skip_withdrawals=True,
            silent=True,
        )


def test_too_large_cl_decrease(pre_cl_balance):
    #  uint256 oneOffCLBalanceDecreaseBP = (MAX_BASIS_POINTS * (_preCLBalance - _unifiedPostCLBalance)) /
    #         _preCLBalance;

    withdrawal_vault_balance = eth_balance(contracts.withdrawal_vault.address)
    max_cl_decrease = (
        ONE_OFF_CL_BALANCE_DECREASE_BP_LIMIT * pre_cl_balance // MAX_BASIS_POINTS + withdrawal_vault_balance
    )

    error_cl_decrease = max_cl_decrease + ETH(1000)
    error_one_off_cl_decrease_bp = (MAX_BASIS_POINTS * (error_cl_decrease - withdrawal_vault_balance)) // pre_cl_balance
    with reverts(encode_error("IncorrectCLBalanceDecrease(uint256)", [error_one_off_cl_decrease_bp])):
        oracle_report(cl_diff=-error_cl_decrease, skip_withdrawals=True, silent=True)


def test_withdrawal_vault_report_more():
    withdrawal_vault_balance = eth_balance(contracts.withdrawal_vault.address)
    with reverts(encode_error("IncorrectWithdrawalsVaultBalance(uint256)", [withdrawal_vault_balance])):
        oracle_report(withdrawalVaultBalance=withdrawal_vault_balance + 1, skip_withdrawals=True, silent=True)


def test_el_vault_report_more():
    el_vault_balance = eth_balance(contracts.execution_layer_rewards_vault.address)
    with reverts(encode_error("IncorrectELRewardsVaultBalance(uint256)", [el_vault_balance])):
        oracle_report(elRewardsVaultBalance=el_vault_balance + 1, skip_withdrawals=True, silent=True)


def test_shares_on_burner_report_more():
    (cover_shares, non_cover_shares) = contracts.burner.getSharesRequestedToBurn()
    shares_requested_to_burn = cover_shares + non_cover_shares
    with reverts(encode_error("IncorrectSharesRequestedToBurn(uint256)", [shares_requested_to_burn])):
        oracle_report(sharesRequestedToBurn=shares_requested_to_burn + 1, skip_withdrawals=True, silent=True)


def test_withdrawal_queue_timestamp(steth_holder):
    (SLOTS_PER_EPOCH, SECONDS_PER_SLOT, GENESIS_TIME) = contracts.hash_consensus_for_accounting_oracle.getChainConfig()
    (refSlot, _) = contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()
    time = chain.time()
    (_, EPOCHS_PER_FRAME, _) = contracts.hash_consensus_for_accounting_oracle.getFrameConfig()
    frame_start_with_offset = GENESIS_TIME + (refSlot + SLOTS_PER_EPOCH * EPOCHS_PER_FRAME + 1) * SECONDS_PER_SLOT
    chain.sleep(frame_start_with_offset - time - REQUEST_TIMESTAMP_MARGIN)
    chain.mine(1)

    request_id = create_withdrawal_request(steth_holder)
    request_timestamp = contracts.withdrawal_queue.getWithdrawalStatus([request_id])[0][3]

    chain.sleep(REQUEST_TIMESTAMP_MARGIN)
    chain.mine(1)

    with reverts(encode_error("IncorrectRequestFinalization(uint256)", [request_timestamp])):
        oracle_report(withdrawalFinalizationBatches=[request_id], silent=True, wait_to_next_report_time=False)


def test_report_deviated_simulated_share_rate(steth_holder):
    simulated_share_rate = 1
    create_withdrawal_request(steth_holder)

    error_msg_start = encode_error("IncorrectSimulatedShareRate(uint256,uint256)", [simulated_share_rate])
    with reverts(revert_pattern=f"{error_msg_start}.*"):
        oracle_report(cl_diff=0, simulatedShareRate=simulated_share_rate)


def test_accounting_oracle_too_much_extra_data(extra_data_service):
    item_count = MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT + 1
    extra_data = extra_data_service.collect({(1, 1): 1}, {}, 1, 1)
    with reverts(
        encode_error(
            "MaxAccountingExtraDataItemsCountExceeded(uint256,uint256)",
            [MAX_ACCOUNTING_EXTRA_DATA_LIST_ITEMS_COUNT, item_count],
        )
    ):
        oracle_report(
            extraDataFormat=1,
            extraDataHash=extra_data.data_hash,
            extraDataItemsCount=item_count,
            extraDataList=extra_data.extra_data,
        )


@pytest.mark.skip("ganache throws 'RPCRequestError: Invalid string length' on such long extra data")
def test_accounting_oracle_too_node_ops_per_extra_data_item(extra_data_service):
    item_count = MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT * 10
    extra_data = extra_data_service.collect({(1, i): i for i in range(item_count)}, {}, 1, item_count)
    with reverts(
        encode_error(
            "TooManyNodeOpsPerExtraDataItem(uint256,uint256)",
            [MAX_NODE_OPERATORS_PER_EXTRA_DATA_ITEM_COUNT, item_count],
        )
    ):
        oracle_report(
            extraDataFormat=1,
            extraDataHash=extra_data.data_hash,
            extraDataItemsCount=1,
            extraDataList=extra_data.extra_data,
        )


def test_veb_oracle_too_much_extra_data():
    item_count = MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT + 1

    ref_slot = _wait_for_next_ref_slot()
    validator_key = contracts.node_operators_registry.getSigningKey(1, 1)[0]
    validator = LidoValidator(1, validator_key)
    report, report_hash = prepare_exit_bus_report([((i, i), validator) for i in range(item_count)], ref_slot)

    with reverts(
        encode_error(
            "IncorrectNumberOfExitRequestsPerReport(uint256)",
            [MAX_VALIDATOR_EXIT_REQUESTS_PER_REPORT],
        )
    ):
        send_report_with_consensus(ref_slot, report, report_hash)


def fake_deposited_validators_increase(cl_validators_diff):
    (deposited, _, _) = contracts.lido.getBeaconStat()

    voting = accounts.at(contracts.voting.address, force=True)
    contracts.acl.createPermission(
        voting,
        contracts.lido,
        web3.keccak(text="UNSAFE_CHANGE_DEPOSITED_VALIDATORS_ROLE"),
        voting,
        {"from": voting},
    )

    contracts.lido.unsafeChangeDepositedValidators(deposited + cl_validators_diff, {"from": voting})


def create_withdrawal_request(steth_holder):
    contracts.lido.approve(contracts.withdrawal_queue.address, ETH(1), {"from": steth_holder})
    contracts.withdrawal_queue.requestWithdrawals([ETH(1)], steth_holder, {"from": steth_holder})

    return contracts.withdrawal_queue.getLastRequestId()


def _wait_for_next_ref_slot():
    wait_to_next_available_report_time(contracts.hash_consensus_for_validators_exit_bus_oracle)
    ref_slot, _ = contracts.hash_consensus_for_validators_exit_bus_oracle.getCurrentFrame()
    return ref_slot


def send_report_with_consensus(ref_slot, report, report_hash):
    consensus_version = contracts.validators_exit_bus_oracle.getConsensusVersion()
    contract_version = contracts.validators_exit_bus_oracle.getContractVersion()

    submitter = reach_consensus(
        ref_slot, report_hash, consensus_version, contracts.hash_consensus_for_validators_exit_bus_oracle
    )

    return contracts.validators_exit_bus_oracle.submitReportData(report, contract_version, {"from": submitter})
