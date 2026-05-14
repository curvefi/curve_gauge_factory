import pytest

import boa


CONTRACTS_PATH = "contracts/"

GAUGE_FACTORY_DEPLOYER = boa.load_partial(CONTRACTS_PATH + "GaugeFactory.vy")
LIQUIDITY_GAUGE_DEPLOYER = boa.load_partial(CONTRACTS_PATH + "LiquidityGauge.vy")


@pytest.fixture(scope="session")
def owner():
    addr = boa.env.generate_address()
    boa.env.set_balance(addr, 10**21)
    return addr


@pytest.fixture(scope="session")
def alice():
    addr = boa.env.generate_address()
    boa.env.set_balance(addr, 10**21)
    return addr


@pytest.fixture(scope="session")
def bob():
    addr = boa.env.generate_address()
    boa.env.set_balance(addr, 10**21)
    return addr


@pytest.fixture(scope="session")
def manager():
    addr = boa.env.generate_address()
    boa.env.set_balance(addr, 10**21)
    return addr


@pytest.fixture(scope="function")
def gauge_factory(owner):
    with boa.env.prank(owner):
        return GAUGE_FACTORY_DEPLOYER.deploy()


@pytest.fixture(scope="session")
def mock_gauge_deployer():
    source = """
# pragma version 0.3.10

lp_token: public(address)
manager: public(address)
factory: public(address)


@external
def __init__(_lp_token: address, _manager: address):
    self.lp_token = _lp_token
    self.manager = _manager
    self.factory = msg.sender
"""
    return boa.loads_partial(source, name="MockGauge")


@pytest.fixture(scope="session")
def mock_gauge_blueprint(mock_gauge_deployer):
    return mock_gauge_deployer.deploy_as_blueprint()


@pytest.fixture(scope="session")
def lp_token():
    source = """
# pragma version 0.3.10

@view
@external
def symbol() -> String[32]:
    return "LP"
"""
    return boa.loads_partial(source, name="MockLP").deploy()


@pytest.fixture(scope="session")
def liquidity_gauge_deployer():
    return LIQUIDITY_GAUGE_DEPLOYER
