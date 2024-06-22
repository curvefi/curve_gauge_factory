# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version paris
"""
@title CurveLiquidityGaugeFactory
@author Curve.Fi
@license Copyright (c) Curve.Fi, 2020-2023 - all rights reserved
@notice Implementation contract for use with Curve Factory
@dev Differs from v5.0.0 in that it uses create_from_blueprint to deploy Gauges
"""

event DeployedGauge:
    _implementation: indexed(address)
    _lp_token: indexed(address)
    _deployer: indexed(address)
    _gauge: address

event UpdateImplementation:
    _old_implementation: address
    _new_implementation: address

event TransferOwnership:
    _old_owner: address
    _new_owner: address


WEEK: constant(uint256) = 86400 * 7

get_implementation: public(address)
owner: public(address)
future_owner: public(address)


gauge_data: public(HashMap[address, uint256])
# user -> gauge -> value

get_gauge_from_lp_token: public(HashMap[address, address])
get_gauge_count: public(uint256)
get_gauge: public(address[MAX_INT128])


@external
def __init__():
    self.owner = msg.sender


@external
def deploy_gauge(_lp_token: address, _manager: address = msg.sender) -> address:
    """
    @notice Deploy a liquidity gauge
    @param _lp_token The token to deposit in the gauge
    @param _manager The address to set as manager of the gauge
    """
    if self.get_gauge_from_lp_token[_lp_token] != ZERO_ADDRESS:
        # overwriting lp_token -> gauge mapping requires
        assert msg.sender == self.owner  # dev: only owner

    gauge_data: uint256 = 1  # set is_valid_gauge = True
    implementation: address = self.get_implementation

    gauge: address = create_from_blueprint(
        implementation,
        _pool,
        code_offset=3,
    )

    self.gauge_data[gauge] = gauge_data

    idx: uint256 = self.get_gauge_count
    self.get_gauge[idx] = gauge
    self.get_gauge_count = idx + 1
    self.get_gauge_from_lp_token[_lp_token] = gauge

    log DeployedGauge(implementation, _lp_token, msg.sender, gauge)

    return gauge


@external
def set_implementation(_implementation: address):
    """
    @notice Set the implementation
    @param _implementation The address of the implementation to use
    """
    assert msg.sender == self.owner  # dev: only owner

    log UpdateImplementation(self.get_implementation, _implementation)
    self.get_implementation = _implementation


@external
def commit_transfer_ownership(_future_owner: address):
    """
    @notice Transfer ownership to `_future_owner`
    @param _future_owner The account to commit as the future owner
    """
    assert msg.sender == self.owner  # dev: only owner

    self.future_owner = _future_owner


@external
def accept_transfer_ownership():
    """
    @notice Accept the transfer of ownership
    @dev Only the committed future owner can call this function
    """
    assert msg.sender == self.future_owner  # dev: only future owner

    log TransferOwnership(self.owner, msg.sender)
    self.owner = msg.sender


@view
@external
def is_valid_gauge(_gauge: address) -> bool:
    """
    @notice Query whether the gauge is a valid one deployed via the factory
    @param _gauge The address of the gauge of interest
    """
    return self.gauge_data[_gauge] != 0
