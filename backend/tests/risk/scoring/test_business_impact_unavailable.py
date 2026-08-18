from app.baseline.schemas import Percentiles
from app.risk.scoring.business_impact import compute_business_impact


def _percentiles() -> Percentiles:
    return Percentiles(p25=500.0, p50=1500.0, p75=4000.0, p95=15000.0, p99=40000.0)


def test_member_harm_always_marked_unavailable():
    result = compute_business_impact([1000.0, 2000.0], baseline_amount_percentiles=_percentiles())
    member_harm = next(c for c in result.components if c.name == "member_harm_impact")
    assert member_harm.status == "unavailable"
    assert member_harm.value is None
    assert member_harm.reason


def test_dollar_exposure_computed_from_real_amounts_when_baseline_supplied():
    amounts = [1000.0, 2000.0]
    result = compute_business_impact(amounts, baseline_amount_percentiles=_percentiles())
    dollar_exposure = next(c for c in result.components if c.name == "dollar_exposure")
    assert dollar_exposure.status == "computed"
    assert dollar_exposure.value is not None
    assert 0.0 <= dollar_exposure.value <= 100.0


def test_business_impact_never_treats_unavailable_as_zero_in_the_sum():
    amounts = [1000.0, 2000.0]
    result = compute_business_impact(amounts, baseline_amount_percentiles=_percentiles())
    computed = [c.value for c in result.components if c.status == "computed"]
    hand_computed_mean = sum(computed) / len(computed)
    assert result.business_impact == hand_computed_mean
    assert result.has_unavailable_components is True  # member_harm/provider_reputation always are


def test_dollar_exposure_unavailable_when_all_amounts_missing():
    result = compute_business_impact([], baseline_amount_percentiles=_percentiles())
    dollar_exposure = next(c for c in result.components if c.name == "dollar_exposure")
    assert dollar_exposure.status == "unavailable"
    assert dollar_exposure.value is None
    # every component is unavailable -- the summary float is a mean-of-
    # nothing 0.0, not a "measured zero impact" -- has_unavailable_components
    # is what a caller must check.
    assert result.business_impact == 0.0
    assert result.has_unavailable_components is True


def test_dollar_exposure_unavailable_when_no_baseline_supplied():
    result = compute_business_impact([1000.0, 2000.0], baseline_amount_percentiles=None)
    dollar_exposure = next(c for c in result.components if c.name == "dollar_exposure")
    assert dollar_exposure.status == "unavailable"
