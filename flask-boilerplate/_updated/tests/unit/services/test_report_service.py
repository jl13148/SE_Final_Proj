import unittest
from unittest.mock import MagicMock, patch
from app.services.report_service import ReportService
from app.models import GlucoseRecord, BloodPressureRecord
import io
import csv
from datetime import datetime
from PyPDF2 import PdfReader

class TestReportService(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock()
        self.user_id = 1
        self.report_service = ReportService(self.mock_db, self.user_id)

    @patch('app.services.report_service.GlucoseRecord')
    @patch('app.services.report_service.BloodPressureRecord')
    def test_generate_csv_report_with_records(self, mock_bp_record, mock_glucose_record):
        # Mock glucose records
        mock_glucose_records = [
            MagicMock(date='2023-09-01', time='08:00:00', glucose_level=120),
            MagicMock(date='2023-09-02', time='09:00:00', glucose_level=130)
        ]
        mock_glucose_record.query.filter_by.return_value.order_by.return_value.all.return_value = mock_glucose_records

        # Mock blood pressure records
        mock_bp_records = [
            MagicMock(date='2023-09-01', time='08:00:00', systolic=120, diastolic=80),
            MagicMock(date='2023-09-02', time='09:00:00', systolic=130, diastolic=85)
        ]
        mock_bp_record.query.filter_by.return_value.order_by.return_value.all.return_value = mock_bp_records

        # Generate CSV report
        output = self.report_service.generate_csv_report()

        # Read CSV content
        output.seek(0)
        csv_content = io.StringIO(output.read().decode('utf-8'))
        csv_reader = csv.reader(csv_content)
        rows = list(csv_reader)

        # Expected CSV content
        expected_rows = [
            ['Glucose Levels'],
            ['Date', 'Time', 'Glucose Level (mg/dL)'],
            ['2023-09-01', '08:00:00', '120'],
            ['2023-09-02', '09:00:00', '130'],
            [],
            ['Blood Pressure Levels'],
            ['Date', 'Time', 'Systolic (mm Hg)', 'Diastolic (mm Hg)'],
            ['2023-09-01', '08:00:00', '120', '80'],
            ['2023-09-02', '09:00:00', '130', '85']
        ]

        self.assertEqual(rows, expected_rows)

    @patch('app.services.report_service.GlucoseRecord')
    @patch('app.services.report_service.BloodPressureRecord')
    def test_generate_csv_report_no_records(self, mock_bp_record, mock_glucose_record):
        # Mock no glucose records
        mock_glucose_record.query.filter_by.return_value.order_by.return_value.all.return_value = []

        # Mock no blood pressure records
        mock_bp_record.query.filter_by.return_value.order_by.return_value.all.return_value = []

        # Generate CSV report
        output = self.report_service.generate_csv_report()

        # Read CSV content
        output.seek(0)
        csv_content = io.StringIO(output.read().decode('utf-8'))
        csv_reader = csv.reader(csv_content)
        rows = list(csv_reader)

        # Expected CSV content
        expected_rows = [
            ['Glucose Levels'],
            ['Date', 'Time', 'Glucose Level (mg/dL)'],
            ['No glucose records found.'],
            [],
            ['Blood Pressure Levels'],
            ['Date', 'Time', 'Systolic (mm Hg)', 'Diastolic (mm Hg)'],
            ['No blood pressure records found.']
        ]

        self.assertEqual(rows, expected_rows)

    @patch('app.services.report_service.GlucoseRecord')
    @patch('app.services.report_service.BloodPressureRecord')
    def test_generate_pdf_report_with_records(self, mock_bp_record, mock_glucose_record):
        # Mock glucose records
        mock_glucose_records = [
            MagicMock(date='2023-09-01', time='08:00:00', glucose_level=120),
            MagicMock(date='2023-09-02', time='09:00:00', glucose_level=130)
        ]
        mock_glucose_record.query.filter_by.return_value.order_by.return_value.all.return_value = mock_glucose_records

        # Mock blood pressure records
        mock_bp_records = [
            MagicMock(date='2023-09-01', time='08:00:00', systolic=120, diastolic=80),
            MagicMock(date='2023-09-02', time='09:00:00', systolic=130, diastolic=85)
        ]
        mock_bp_record.query.filter_by.return_value.order_by.return_value.all.return_value = mock_bp_records

        buffer = self.report_service.generate_pdf_report()

        self.assertNotEqual(buffer.getbuffer().nbytes, 0)

        # Read PDF content using PyPDF2
        buffer.seek(0)
        reader = PdfReader(buffer)
        text = ""
        for page in reader.pages:
            text += page.extract_text()

        # Check for expected text in PDF
        self.assertIn("Health Report", text)
        self.assertIn("Report Date:", text)
        self.assertIn("Glucose Levels:", text)
        self.assertIn("Date: 2023-09-01", text)
        self.assertIn("Time: 08:00:00", text)
        self.assertIn("Glucose Level: 120 mg/dL", text)
        self.assertIn("Blood Pressure Levels:", text)
        self.assertIn("Systolic: 120 mm Hg", text)
        self.assertIn("Diastolic: 80 mm Hg", text)
        self.assertIn("Summary:", text)
        self.assertIn("This report contains your logged health data entries,", text)

    @patch('app.services.report_service.GlucoseRecord')
    @patch('app.services.report_service.BloodPressureRecord')
    def test_generate_pdf_report_no_records(self, mock_bp_record, mock_glucose_record):
        # Mock no glucose records
        mock_glucose_record.query.filter_by.return_value.order_by.return_value.all.return_value = []

        # Mock no blood pressure records
        mock_bp_record.query.filter_by.return_value.order_by.return_value.all.return_value = []

        buffer = self.report_service.generate_pdf_report()

        self.assertNotEqual(buffer.getbuffer().nbytes, 0)

        # Read PDF content using PyPDF2
        buffer.seek(0)
        reader = PdfReader(buffer)
        text = ""
        for page in reader.pages:
            text += page.extract_text()

        # Check for expected text in PDF
        self.assertIn("Health Report", text)
        self.assertIn("Report Date:", text)
        self.assertIn("Glucose Levels:", text)
        self.assertIn("No glucose records found.", text)
        self.assertIn("Blood Pressure Levels:", text)
        self.assertIn("No blood pressure records found.", text)
        self.assertIn("Summary:", text)
        self.assertIn("This report contains your logged health data entries,", text)

    @patch('app.services.report_service.GlucoseRecord')
    @patch('app.services.report_service.BloodPressureRecord')
    def test_generate_pdf_report_page_break(self, mock_bp_record, mock_glucose_record):
        # Mock a large number of glucose records to trigger page breaks
        mock_glucose_records = [
            MagicMock(date='2023-09-01', time='08:00:00', glucose_level=120 + i)
            for i in range(50)  # Adjust the number to ensure multiple pages
        ]
        mock_glucose_record.query.filter_by.return_value.order_by.return_value.all.return_value = mock_glucose_records

        # Mock a large number of blood pressure records
        mock_bp_records = [
            MagicMock(date='2023-09-01', time='08:00:00', systolic=120 + i, diastolic=80 + i)
            for i in range(50)
        ]
        mock_bp_record.query.filter_by.return_value.order_by.return_value.all.return_value = mock_bp_records

        # Generate PDF report
        buffer = self.report_service.generate_pdf_report()

        # Verify buffer is not empty
        self.assertNotEqual(buffer.getbuffer().nbytes, 0)

        # Read PDF content using PyPDF2
        buffer.seek(0)
        reader = PdfReader(buffer)
        num_pages = len(reader.pages)

        # Check that multiple pages are created
        self.assertGreater(num_pages, 1)

        # Optionally, verify content on the first and last pages
        first_page_text = reader.pages[0].extract_text()
        last_page_text = reader.pages[-1].extract_text()

        self.assertIn("Health Report", first_page_text)
        self.assertIn("Summary:", last_page_text)

if __name__ == '__main__':
    unittest.main()