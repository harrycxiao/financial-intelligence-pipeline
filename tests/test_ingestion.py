from src.ingestion.company_ingestion import fetch_company_metadata
from src.database.store import store_company


def test_company_ingestion_and_storage():
    metadata = fetch_company_metadata("AAPL")
    company = store_company(metadata)

    print(company.id)
    print(company.ticker)
    print(company.name)
    print(company.exchange)


if __name__ == "__main__":
    test_company_ingestion_and_storage()