from brownie import ShapellaUpgradeTemplate, interface
from brownie.network.account import LocalAccount
from utils.config import (
    contracts,
    LIDO_LOCATOR_IMPL,
    LIDO_V2_UPGRADE_TEMPLATE,
    prompt_bool,
    get_priority_fee,
    get_max_fee,
    get_is_live,
    get_deployer_account,
    DEPLOYER_EOA_LOCATOR,
)

# Private constant taken from Lido contract
INITIAL_TOKEN_HOLDER = "0x000000000000000000000000000000000000dEaD"

TIMESTAMP_FIRST_SECOND_OF_JULY_2023_UTC = 1688169600


def ask_shapella_upgrade_confirmation(template_address, locator_implementation):
    print(f"!!! Going to do preliminary shapella upgrade actions. Namely:")
    print(f"  - upgrade LidoLocator proxy implementation to {locator_implementation}")
    print(f"  - transfer OZ admin and proxy ownership to the upgrade template {template_address}.")
    print(f"This is IRREVERSIBLE!")
    print("Does it look good? [yes/no]")
    resume = prompt_bool()
    while resume is None:
        resume = prompt_bool()
    if not resume:
        raise RuntimeError("User termination execution")


def get_tx_params(deployer):
    tx_params = {"from": deployer}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()
        tx_params["max_fee"] = get_max_fee()
    return tx_params


def assert_locator_deployer_eoa_is_impersonated():
    assert not get_is_live(), "Must not run any preliminary steps on live network!"
    deployer_account = get_deployer_account()
    assert not isinstance(deployer_account, LocalAccount), "mainnet deployer oea must be impersonated in tests"
    assert get_deployer_account() != DEPLOYER_EOA_LOCATOR


def prepare_upgrade_locator_impl(admin):
    assert_locator_deployer_eoa_is_impersonated()

    assert interface.OssifiableProxy(contracts.lido_locator).proxy__getAdmin() == admin
    interface.OssifiableProxy(contracts.lido_locator).proxy__upgradeTo(LIDO_LOCATOR_IMPL, get_tx_params(admin))
    print(f"=== Upgrade lido locator implementation to {LIDO_LOCATOR_IMPL} ===")


def prepare_transfer_locator_ownership_to_template(admin, template):
    assert_locator_deployer_eoa_is_impersonated()
    interface.OssifiableProxy(contracts.lido_locator).proxy__changeAdmin(template, get_tx_params(admin))


def prepare_for_shapella_upgrade_voting(silent=False):
    if not silent:
        ask_shapella_upgrade_confirmation(LIDO_V2_UPGRADE_TEMPLATE, LIDO_LOCATOR_IMPL)

    # To get sure the "stone" is in place
    assert contracts.lido.balanceOf(INITIAL_TOKEN_HOLDER) > 0

    prepare_upgrade_locator_impl(DEPLOYER_EOA_LOCATOR)

    prepare_transfer_locator_ownership_to_template(DEPLOYER_EOA_LOCATOR, LIDO_V2_UPGRADE_TEMPLATE)

    return ShapellaUpgradeTemplate.at(LIDO_V2_UPGRADE_TEMPLATE)
