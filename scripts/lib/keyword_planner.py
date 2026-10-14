from google.ads.googleads.client import GoogleAdsClient


def map_competition(level) -> str:
    return level.name if level is not None else "UNKNOWN"


def micros_to_currency(micros) -> float:
    if micros is None:
        return 0.0
    return micros / 1_000_000


def generate_keyword_ideas(
    client: GoogleAdsClient,
    customer_id: str,
    keywords=None,
    url=None,
    location_ids=("2554",),
    language_id="1000",
    min_avg_monthly_searches=0,
):
    """Queries Keyword Planner for keyword ideas.

    location_ids: iterable of geo target constant IDs (see resolve_location.py
    to look these up by place name). Multiple locations are combined into one
    request (e.g. several towns in a region).
    """
    keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")

    location_rns = [f"geoTargetConstants/{lid}" for lid in location_ids]
    # LanguageConstantService was removed from the API; the resource name
    # format (languageConstants/{criterion_id}) is stable, so build it directly.
    language_rn = f"languageConstants/{language_id}"

    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = customer_id
    request.language = language_rn
    request.geo_target_constants = location_rns
    request.include_adult_keywords = False
    request.keyword_plan_network = (
        client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS
    )

    keywords = keywords or []
    if keywords and url:
        request.keyword_and_url_seed.url = url
        request.keyword_and_url_seed.keywords.extend(keywords)
    elif url:
        request.url_seed.url = url
    else:
        request.keyword_seed.keywords.extend(keywords)

    response = keyword_plan_idea_service.generate_keyword_ideas(request=request, timeout=120)

    results = []
    for idea in response:
        metrics = idea.keyword_idea_metrics
        if metrics.avg_monthly_searches < min_avg_monthly_searches:
            continue
        results.append(
            {
                "keyword": idea.text,
                "avg_monthly_searches": metrics.avg_monthly_searches,
                "competition": map_competition(metrics.competition),
                "competition_index": metrics.competition_index,
                "low_top_of_page_bid": micros_to_currency(metrics.low_top_of_page_bid_micros),
                "high_top_of_page_bid": micros_to_currency(metrics.high_top_of_page_bid_micros),
            }
        )

    results.sort(key=lambda r: r["avg_monthly_searches"], reverse=True)
    return results


def get_keyword_historical_metrics(
    client: GoogleAdsClient,
    customer_id: str,
    keywords,
    location_ids,
    language_id="1000",
):
    """Looks up exact-match historical metrics for specific keyword phrases
    (as opposed to generate_keyword_ideas, which expands seeds into new
    suggestions). Used for step 2's location-combined phrases, where we
    already know the exact phrase and just want its own volume/competition.

    geo_target_constants is capped at 10 per request by the API, so callers
    targeting more locations than that should call this once per location
    (or in batches of <=10) rather than passing them all at once - metrics
    returned are aggregated across whatever locations are passed in a single
    call, not broken out per location.
    """
    keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")

    location_rns = [f"geoTargetConstants/{lid}" for lid in location_ids]
    language_rn = f"languageConstants/{language_id}"

    request = client.get_type("GenerateKeywordHistoricalMetricsRequest")
    request.customer_id = customer_id
    request.keywords.extend(keywords)
    request.language = language_rn
    request.geo_target_constants = location_rns
    request.keyword_plan_network = (
        client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS
    )

    response = keyword_plan_idea_service.generate_keyword_historical_metrics(
        request=request, timeout=120
    )

    results = []
    for r in response.results:
        metrics = r.keyword_metrics
        results.append(
            {
                "keyword": r.text,
                "avg_monthly_searches": metrics.avg_monthly_searches,
                "competition": map_competition(metrics.competition),
                "competition_index": metrics.competition_index,
                "low_top_of_page_bid": micros_to_currency(metrics.low_top_of_page_bid_micros),
                "high_top_of_page_bid": micros_to_currency(metrics.high_top_of_page_bid_micros),
            }
        )
    return results


def resolve_locations(client: GoogleAdsClient, location_names, locale="en", country_code="NZ"):
    """Resolves place names (e.g. 'Palmerston North') to geo target constants.

    Returns a list of dicts: id, name, country_code, target_type, resource_name.
    """
    geo_target_constant_service = client.get_service("GeoTargetConstantService")
    request = client.get_type("SuggestGeoTargetConstantsRequest")
    request.locale = locale
    request.country_code = country_code
    request.location_names.names.extend(location_names)

    response = geo_target_constant_service.suggest_geo_target_constants(request=request, timeout=60)

    results = []
    for suggestion in response.geo_target_constant_suggestions:
        gtc = suggestion.geo_target_constant
        results.append(
            {
                "id": gtc.id,
                "name": gtc.name,
                "country_code": gtc.country_code,
                "target_type": gtc.target_type,
                "resource_name": gtc.resource_name,
            }
        )
    return results
