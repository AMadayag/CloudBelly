import io
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call

sys.path.append(os.path.abspath("lambda/collection"))

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "sample_data.xlsx")

@pytest.fixture
def scraper():
  from collection.spiders.www_abs_gov_au.total_value_of_dwellings import TotalValueOfDwellingsScraper
  s = TotalValueOfDwellingsScraper()
  s.pipeline = MagicMock()
  return s

@pytest.fixture
def xlsx_response():
  mock = MagicMock()
  with open(FIXTURE_PATH, "rb") as f:
    mock.content = f.read()
  return mock

# parse()
class TestParse:
  def test_extracts_xlsx_href_and_fetches_it(self, scraper):
    fake_html = b"""
    <html><body>
      <div>
        <div><div><h3>Median price and number of transfers (capital city and rest of state)</h3></div></div>
        <a href="/download/sample.xlsx">Download</a>
      </div>
    </body></html>
    """
    html_response = MagicMock()
    html_response.content = fake_html

    xlsx_response = MagicMock()
    xlsx_response.content = open(FIXTURE_PATH, "rb").read()

    with patch("collection.spiders.www_abs_gov_au.total_value_of_dwellings.requests.get",
      return_value=xlsx_response) as mock_get:
      scraper.parse(html_response)

    mock_get.assert_called_once_with("https://www.abs.gov.au/download/sample.xlsx")

  def test_parse_calls_parse_data_sheet(self, scraper):
    fake_html = b"""
    <html><body>
      <div>
        <div><div><h3>Median price and number of transfers (capital city and rest of state)</h3></div></div>
        <a href="/download/sample.xlsx">Download</a>
      </div>
    </body></html>
    """
    html_response = MagicMock()
    html_response.content = fake_html

    xlsx_response = MagicMock()
    xlsx_response.content = open(FIXTURE_PATH, "rb").read()

    with patch("collection.spiders.www_abs_gov_au.total_value_of_dwellings.requests.get",
            return_value=xlsx_response):
      with patch.object(scraper, "parseDataSheet") as mock_parse_data_sheet:
        scraper.parse(html_response)

    mock_parse_data_sheet.assert_called_once()

# parseDataSheet()
class TestParseDataSheet:
  def test_process_item_called_for_each_area_and_date(self, scraper, xlsx_response):
    scraper.parseDataSheet(xlsx_response)
    # 2 areas (NSW, Victoria) x 3 dates = 6 calls
    assert scraper.pipeline.processItem.call_count == 6

    def test_item_has_required_keys(self, scraper, xlsx_response):
      scraper.parseDataSheet(xlsx_response)
      item = scraper.pipeline.processItem.call_args_list[0][0][0]
      assert "date" in item
      assert "area" in item
      assert "median_price_of_established_house_transfers" in item
      assert "median_price_of_attached_dwelling_transfers" in item
      assert "number_of_established_house_transfers" in item
      assert "number_of_attached_dwelling_transfers" in item

    def test_price_multiplied_by_1000(self, scraper, xlsx_response):
      """Raw xlsx value of 950 should become 950000."""
      scraper.parseDataSheet(xlsx_response)
      items = [call[0][0] for call in scraper.pipeline.processItem.call_args_list]
      nsw_first = next(i for i in items if i["area"] == "New South Wales" and i["date"] == "Sep-2023")
      assert nsw_first["median_price_of_established_house_transfers"] == 950000
      assert nsw_first["median_price_of_attached_dwelling_transfers"] == 720000

    def test_area_extracted_from_column_header(self, scraper, xlsx_response):
      """Area should be the second-to-last segment of the semicolon-delimited header."""
      scraper.parseDataSheet(xlsx_response)
      items = [call[0][0] for call in scraper.pipeline.processItem.call_args_list]
      areas = {i["area"] for i in items}
      assert "New South Wales" in areas
      assert "Victoria" in areas

    def test_dates_are_strings(self, scraper, xlsx_response):
      """Dates should come through as plain strings, not datetime objects."""
      scraper.parseDataSheet(xlsx_response)
      items = [call[0][0] for call in scraper.pipeline.processItem.call_args_list]
      for item in items:
        assert isinstance(item["date"], str)

    def test_null_values_passed_through_as_none(self, scraper):
      """Blank cells in the xlsx should produce None, not NaN."""
      import pandas as pd

      # Build a response where house price is blank for one row
      rows = [
        [None] * 10 + ["Sep-2023"],
        ["Median Price of Established House Transfers ; New South Wales ;"] + [None] * 9 + [None],  # blank
        ["Median Price of Attached Dwelling Transfers ; New South Wales ;"] + [None] * 9 + [700],
        ["Number of Established House Transfers ; New South Wales ;"] + [None] * 9 + [50],
        ["Number of Attached Dwelling Transfers ; New South Wales ;"] + [None] * 9 + [30],
      ]
      df = pd.DataFrame(rows).T
      buf = io.BytesIO()
      df.to_excel(buf, sheet_name="Data1", index=False, header=False)
      buf.seek(0)

      mock_response = MagicMock()
      mock_response.content = buf.read()

      scraper.parseDataSheet(mock_response)

      item = scraper.pipeline.processItem.call_args_list[0][0][0]
      assert item["median_price_of_established_house_transfers"] is None
      assert isinstance(item["median_price_of_established_house_transfers"], type(None))