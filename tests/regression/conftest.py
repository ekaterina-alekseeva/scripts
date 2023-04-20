import pytest

from utils.config import contracts
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes


@pytest.fixture(scope="module", autouse=is_there_any_vote_scripts())
def autoexecute_vote(helpers, vote_ids_from_env, accounts):
    if vote_ids_from_env:
        helpers.execute_votes(accounts, vote_ids_from_env, contracts.voting, topup="0.5 ether")
    else:
        start_and_execute_votes(contracts.voting, helpers)


@pytest.fixture()
def active_lido():
    if contracts.lido.isStopped():
        contracts.lido.resume({"from": contracts.voting})

    if contracts.lido.isStakingPaused():
        contracts.lido.resumeStaking({"from": contracts.voting})


@pytest.fixture()
def stopped_lido():
    if not contracts.lido.isStopped():
        contracts.lido.stop({"from": contracts.voting})

    if not contracts.lido.isStakingPaused():
        contracts.lido.pauseStaking({"from": contracts.voting})
