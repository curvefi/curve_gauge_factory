import boa
import pytest
from eth.exceptions import Revert
from eth_abi import encode
from eth_utils import keccak

CRV = "0xD533a949740bb3306d119CC777fa900bA034cd52"
GAUGE_CONTROLLER = "0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB"
VEBOOST_PROXY = "0x8E0c00ed546602fD9927DF742bbAbF726D5B0d16"
VOTING_ESCROW = "0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2"
WEEK = 604800


@pytest.fixture
def reward_gauge(gauge_factory, owner, manager, liquidity_gauge_deployer):
    with boa.env.anchor():
        dependencies = {
            CRV: """
                # pragma version 0.3.10
                @external
                def future_epoch_time_write() -> uint256:
                    return 2_000_000_000
                @view
                @external
                def rate() -> uint256:
                    return 0
            """,
            GAUGE_CONTROLLER: """
                # pragma version 0.3.10
                @external
                def checkpoint_gauge(_gauge: address):
                    pass
                @view
                @external
                def gauge_relative_weight(_gauge: address, _time: uint256) -> uint256:
                    return 0
            """,
            VEBOOST_PROXY: """
                # pragma version 0.3.10
                @view
                @external
                def adjusted_balance_of(_account: address) -> uint256:
                    return 0
            """,
            VOTING_ESCROW: """
                # pragma version 0.3.10
                @view
                @external
                def totalSupply() -> uint256:
                    return 0
            """,
        }
        for address, source in dependencies.items():
            mock = boa.loads_partial(source).deploy()
            boa.env.set_code(address, boa.env.get_code(mock.address))

        token_source = """
            # pragma version 0.3.10
            balanceOf: public(HashMap[address, uint256])
            allowance: public(HashMap[address, HashMap[address, uint256]])
            fail_transfer: public(bool)
            burn_gas: public(bool)
            sink: uint256

            @view
            @external
            def symbol() -> String[32]:
                return "MOCK"

            @external
            def mint(_to: address, _amount: uint256):
                self.balanceOf[_to] += _amount

            @external
            def set_fail_transfer(_fail: bool):
                self.fail_transfer = _fail

            @external
            def set_burn_gas(_burn: bool):
                self.burn_gas = _burn

            @external
            def approve(_spender: address, _amount: uint256) -> bool:
                self.allowance[msg.sender][_spender] = _amount
                return True

            @external
            def transferFrom(_from: address, _to: address, _amount: uint256) -> bool:
                self.allowance[_from][msg.sender] -= _amount
                self.balanceOf[_from] -= _amount
                self.balanceOf[_to] += _amount
                return True

            @external
            def transfer(_to: address, _amount: uint256) -> bool:
                assert not self.fail_transfer
                if self.burn_gas:
                    for i in range(100_000):
                        self.sink = i
                self.balanceOf[msg.sender] -= _amount
                self.balanceOf[_to] += _amount
                return True
        """
        token_deployer = boa.loads_partial(token_source, name="MockToken")
        lp, bad, good = [token_deployer.deploy() for _ in range(3)]

        blueprint = liquidity_gauge_deployer.deploy_as_blueprint()
        with boa.env.prank(owner):
            gauge_factory.set_implementation(blueprint.address)
            gauge_address = gauge_factory.deploy_gauge(lp.address, manager)
        gauge = liquidity_gauge_deployer.at(gauge_address)
        yield gauge, lp, bad, good


def test_reward_amount_cap(reward_gauge, owner, manager, alice):
    gauge, lp, bad, _ = reward_gauge
    lp.mint(alice, 1)
    with boa.env.prank(alice):
        lp.approve(gauge.address, 1)
        gauge.deposit(1)
    with boa.env.prank(manager):
        gauge.add_reward(bad.address, manager)
    bad.mint(manager, 2**96 + 1)
    with boa.env.prank(manager):
        bad.approve(gauge.address, 2**96 + 1)
        with boa.reverts("Reward overflow"):
            gauge.deposit_reward_token(bad.address, 2**96 + 1, 3 * WEEK // 7)
        gauge.deposit_reward_token(bad.address, 2**96, 3 * WEEK // 7)
        with boa.reverts("Reward overflow"):
            gauge.deposit_reward_token(bad.address, 1, 3 * WEEK // 7)
    assert gauge.reward_remaining(bad.address) == 2**96
    boa.env.time_travel(seconds=1)
    with boa.env.prank(alice):
        gauge.withdraw(1, False)
    assert lp.balanceOf(alice) == 1


def test_invalidating_bad_reward_unblocks_withdrawal(
    reward_gauge, owner, manager, alice, bob
):
    gauge, lp, bad, good = reward_gauge
    lp.mint(alice, 100)
    with boa.env.prank(alice):
        lp.approve(gauge.address, 100)
        gauge.deposit(100)
    with boa.env.prank(manager):
        for token in (bad, good):
            gauge.add_reward(token.address, manager)
            token.mint(manager, WEEK)
            token.approve(gauge.address, WEEK)
            gauge.deposit_reward_token(token.address, WEEK)

    boa.env.time_travel(seconds=100)
    bad.set_fail_transfer(True)
    with boa.env.prank(alice), boa.reverts():
        gauge.withdraw(10, True)
    assert gauge.balanceOf(alice) == 100

    bad.set_fail_transfer(False)
    bad.set_burn_gas(True)
    calldata = keccak(text="withdraw(uint256,bool,address)")[:4] + encode(
        ["uint256", "bool", "address"], [10, True, alice]
    )
    with pytest.raises(Revert):
        boa.env.raw_call(gauge.address, sender=alice, gas=1_000_000, data=calldata)

    with boa.env.prank(bob), boa.reverts():
        gauge.invalidate_reward(bad.address)
    with boa.env.prank(owner):
        gauge.invalidate_reward(bad.address)
    assert gauge.invalidated_reward(bad.address)
    assert gauge.claimable_reward(alice, bad.address) == 0

    boa.env.raw_call(gauge.address, sender=alice, gas=1_000_000, data=calldata)
    with boa.env.prank(alice):
        gauge.claim_rewards()
    assert gauge.balanceOf(alice) == 90
    assert lp.balanceOf(alice) == 10
    assert bad.balanceOf(alice) == 0
    assert good.balanceOf(alice) > 0

    with boa.env.prank(manager):
        with boa.reverts():
            gauge.deposit_reward_token(bad.address, 1)
        gauge.set_reward_distributor(bad.address, bob)
    assert gauge.invalidated_reward(bad.address)
    with boa.env.prank(owner), boa.reverts():
        gauge.invalidate_reward(bad.address)
