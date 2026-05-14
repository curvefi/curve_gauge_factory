import boa


def test_constructor(gauge_factory, owner):
    assert gauge_factory.owner() == owner


def test_set_implementation(gauge_factory, alice, mock_gauge_blueprint):
    with boa.reverts():
        with boa.env.prank(alice):
            gauge_factory.set_implementation(mock_gauge_blueprint.address)

    with boa.env.prank(gauge_factory.owner()):
        gauge_factory.set_implementation(mock_gauge_blueprint.address)

    assert gauge_factory.get_implementation() == mock_gauge_blueprint.address


def test_commit_and_accept_transfer_ownership(gauge_factory, owner, alice):
    with boa.reverts():
        with boa.env.prank(alice):
            gauge_factory.commit_transfer_ownership(alice)

    with boa.env.prank(owner):
        gauge_factory.commit_transfer_ownership(alice)

    assert gauge_factory.future_owner() == alice

    with boa.reverts():
        with boa.env.prank(owner):
            gauge_factory.accept_transfer_ownership()

    with boa.env.prank(alice):
        gauge_factory.accept_transfer_ownership()

    assert gauge_factory.owner() == alice


def test_deploy_gauge(
    gauge_factory, owner, manager, lp_token, mock_gauge_deployer, mock_gauge_blueprint
):
    with boa.env.prank(owner):
        gauge_factory.set_implementation(mock_gauge_blueprint.address)
        gauge_address = gauge_factory.deploy_gauge(lp_token.address, manager)

    gauge = mock_gauge_deployer.at(gauge_address)

    assert gauge.lp_token() == lp_token.address
    assert gauge.manager() == manager
    assert gauge.factory() == gauge_factory.address
    assert gauge_factory.is_valid_gauge(gauge_address) is True
    assert gauge_factory.gauge_data(gauge_address) == 1
    assert gauge_factory.get_gauge_count() == 1
    assert gauge_factory.get_gauge(0) == gauge_address
    assert gauge_factory.get_gauge_from_lp_token(lp_token.address) == gauge_address


def test_deploy_gauge_duplicate(
    gauge_factory, owner, alice, manager, bob, lp_token, mock_gauge_blueprint
):
    with boa.env.prank(owner):
        gauge_factory.set_implementation(mock_gauge_blueprint.address)
        first_gauge = gauge_factory.deploy_gauge(lp_token.address, manager)

    with boa.reverts():
        with boa.env.prank(alice):
            gauge_factory.deploy_gauge(lp_token.address, bob)

    assert gauge_factory.get_gauge_count() == 1
    assert gauge_factory.get_gauge_from_lp_token(lp_token.address) == first_gauge


def test_overwrite(
    gauge_factory,
    owner,
    manager,
    bob,
    lp_token,
    mock_gauge_deployer,
    mock_gauge_blueprint,
):
    with boa.env.prank(owner):
        gauge_factory.set_implementation(mock_gauge_blueprint.address)
        first_gauge = gauge_factory.deploy_gauge(lp_token.address, manager)
        second_gauge = gauge_factory.deploy_gauge(lp_token.address, bob)

    first = mock_gauge_deployer.at(first_gauge)
    second = mock_gauge_deployer.at(second_gauge)

    assert first.address != second.address
    assert first.manager() == manager
    assert second.manager() == bob
    assert gauge_factory.is_valid_gauge(first_gauge) is True
    assert gauge_factory.is_valid_gauge(second_gauge) is True
    assert gauge_factory.get_gauge_count() == 2
    assert gauge_factory.get_gauge(0) == first_gauge
    assert gauge_factory.get_gauge(1) == second_gauge
    assert gauge_factory.get_gauge_from_lp_token(lp_token.address) == second_gauge
