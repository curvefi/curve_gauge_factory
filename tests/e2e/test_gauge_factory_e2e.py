import pytest

import boa


CRV = "0xD533a949740bb3306d119CC777fa900bA034cd52"


@pytest.fixture(scope="module")
def setup_crv():
    crv_source = """
    # pragma version 0.3.10

    @external
    def future_epoch_time_write() -> uint256:
        return 2_000_000_000


    @view
    @external
    def rate() -> uint256:
        return 123456789
    """
    crv = boa.loads_partial(crv_source, name="MockCRV").deploy()
    boa.env.set_code(CRV, boa.env.get_code(crv.address))


def test_factory_deploys_real_liquidity_gauge(
    gauge_factory,
    owner,
    manager,
    lp_token,
    liquidity_gauge_deployer,
    setup_crv,
):
    blueprint = liquidity_gauge_deployer.deploy_as_blueprint()

    with boa.env.prank(owner):
        gauge_factory.set_implementation(blueprint.address)
        gauge_address = gauge_factory.deploy_gauge(lp_token.address, manager)

    gauge = liquidity_gauge_deployer.at(gauge_address)

    assert gauge_factory.get_gauge_count() == 1
    assert gauge_factory.get_gauge(0) == gauge_address
    assert gauge_factory.get_gauge_from_lp_token(lp_token.address) == gauge_address
    assert gauge_factory.is_valid_gauge(gauge_address) is True

    assert gauge.factory() == gauge_factory.address
    assert gauge.manager() == manager
    assert gauge.lp_token() == lp_token.address
    assert gauge.name() == "Curve.fi LP Gauge Deposit"
    assert gauge.symbol() == "LP-gauge"
    assert gauge.version() == "v6.1.1"
    assert gauge.inflation_rate() == 123456789
    assert gauge.future_epoch_time() == 2_000_000_000
