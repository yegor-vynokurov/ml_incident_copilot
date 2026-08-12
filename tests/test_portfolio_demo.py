from scripts import (
    demo_portfolio,
)


def test_portfolio_demo_is_importable():
    assert callable(
        demo_portfolio.main
    )