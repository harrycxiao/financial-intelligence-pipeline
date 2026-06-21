from datetime import date, timedelta

from src.database import query


TEST_TICKER = "AAPL"


# ---------------------------------------------------------------------
# Company query tests
# ---------------------------------------------------------------------


def test_company_queries() -> None:
    print("\n--- Company query tests ---")

    company = query.get_company_by_ticker(TEST_TICKER)
    print("get_company_by_ticker:")
    print(company)

    company_id = query.get_company_id_by_ticker(TEST_TICKER)
    print("\nget_company_id_by_ticker:")
    print(company_id)

    exists = query.company_exists(TEST_TICKER)
    print("\ncompany_exists:")
    print(exists)

    companies = query.get_all_companies()
    print("\nget_all_companies:")
    print(f"Rows returned: {len(companies)}")
    print(companies[:3])

    if company is not None and company.get("sector") is not None:
        sector_companies = query.get_companies_by_sector(company["sector"])
        print("\nget_companies_by_sector:")
        print(f"Sector: {company['sector']}")
        print(f"Rows returned: {len(sector_companies)}")
        print(sector_companies[:3])


# ---------------------------------------------------------------------
# Market data query tests
# ---------------------------------------------------------------------


def test_market_data_queries() -> None:
    print("\n--- Market data query tests ---")

    latest_price = query.get_latest_market_price(TEST_TICKER)
    print("get_latest_market_price:")
    print(latest_price)

    market_data = query.get_market_data(TEST_TICKER)
    print("\nget_market_data:")
    print(f"Rows returned: {len(market_data)}")
    print(market_data[:3])

    recent_market_data = query.get_recent_market_data(TEST_TICKER, days=30)
    print("\nget_recent_market_data:")
    print(f"Rows returned: {len(recent_market_data)}")
    print(recent_market_data[:3])

    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    market_data_between_dates = query.get_market_data_between_dates(
        ticker=TEST_TICKER,
        start_date=start_date,
        end_date=end_date,
    )

    print("\nget_market_data_between_dates:")
    print(f"Start date: {start_date}")
    print(f"End date: {end_date}")
    print(f"Rows returned: {len(market_data_between_dates)}")
    print(market_data_between_dates[:3])

    count = query.get_market_data_count(TEST_TICKER)
    print("\nget_market_data_count:")
    print(count)


# ---------------------------------------------------------------------
# Financial metrics query tests
# ---------------------------------------------------------------------


def test_financial_metrics_queries() -> None:
    print("\n--- Financial metrics query tests ---")

    latest_metrics = query.get_latest_financial_metrics(TEST_TICKER)
    print("get_latest_financial_metrics:")
    print(latest_metrics)

    metrics = query.get_financial_metrics(TEST_TICKER)
    print("\nget_financial_metrics:")
    print(f"Rows returned: {len(metrics)}")
    print(metrics[:3])

    metrics_between_years = query.get_financial_metrics_between_years(
        ticker=TEST_TICKER,
        start_year=2021,
        end_year=2025,
    )

    print("\nget_financial_metrics_between_years:")
    print("Years: 2021-2025")
    print(f"Rows returned: {len(metrics_between_years)}")
    print(metrics_between_years)

    count = query.get_financial_metrics_count(TEST_TICKER)
    print("\nget_financial_metrics_count:")
    print(count)


# ---------------------------------------------------------------------
# SEC filing query tests
# ---------------------------------------------------------------------


def test_sec_queries() -> None:
    print("\n--- SEC filing query tests ---")

    filings = query.get_sec_filings(TEST_TICKER)
    print("get_sec_filings:")
    print(f"Rows returned: {len(filings)}")
    print(filings[:3])

    latest_filing = query.get_latest_sec_filing(TEST_TICKER)
    print("\nget_latest_sec_filing:")
    print(latest_filing)

    latest_10k = query.get_latest_sec_filing(TEST_TICKER, filing_type="10-K")
    print("\nget_latest_sec_filing, 10-K:")
    print(latest_10k)

    ten_ks = query.get_sec_filings_by_type(TEST_TICKER, filing_type="10-K")
    print("\nget_sec_filings_by_type, 10-K:")
    print(f"Rows returned: {len(ten_ks)}")
    print(ten_ks)

    recent_filings = query.get_recent_sec_filings(TEST_TICKER, limit=5)
    print("\nget_recent_sec_filings:")
    print(f"Rows returned: {len(recent_filings)}")
    print(recent_filings)

    if latest_filing is not None:
        filing_by_accession = query.get_filing_by_accession_number(
            latest_filing["accession_number"],
            include_raw_text=False,
        )

        print("\nget_filing_by_accession_number:")
        print(filing_by_accession)


# ---------------------------------------------------------------------
# News article query tests
# ---------------------------------------------------------------------


def test_news_queries() -> None:
    print("\n--- News article query tests ---")

    articles = query.get_news_articles(TEST_TICKER)
    print("get_news_articles:")
    print(f"Rows returned: {len(articles)}")
    print(articles[:3])

    recent_articles = query.get_recent_news_articles(TEST_TICKER, days=30)
    print("\nget_recent_news_articles:")
    print(f"Rows returned: {len(recent_articles)}")
    print(recent_articles[:3])

    latest_article = query.get_latest_news_article(TEST_TICKER)
    print("\nget_latest_news_article:")
    print(latest_article)

    yahoo_articles = query.get_news_articles_by_source(TEST_TICKER, source="Yahoo")
    print("\nget_news_articles_by_source, Yahoo:")
    print(f"Rows returned: {len(yahoo_articles)}")
    print(yahoo_articles[:3])

    searched_articles = query.search_news_articles(TEST_TICKER, keyword="Apple")
    print("\nsearch_news_articles, keyword='Apple':")
    print(f"Rows returned: {len(searched_articles)}")
    print(searched_articles[:3])

    if latest_article is not None:
        article_by_url = query.get_news_article_by_url(
            latest_article["url"],
            include_raw_text=False,
        )

        print("\nget_news_article_by_url:")
        print(article_by_url)


if __name__ == "__main__":
    test_company_queries()
    test_market_data_queries()
    test_financial_metrics_queries()
    test_sec_queries()
    test_news_queries()
