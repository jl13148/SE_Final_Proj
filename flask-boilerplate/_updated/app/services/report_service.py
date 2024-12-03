import io
import csv
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from app.models import GlucoseRecord, BloodPressureRecord

class ReportService:
    def __init__(self, db, user_id):
        self.db = db
        self.user_id = user_id

    def generate_csv_report(self):
        """
        Generate CSV data for the user's health records.
        """
        si = io.StringIO()
        cw = csv.writer(si)

        # Write Glucose Records
        cw.writerow(['Glucose Levels'])
        cw.writerow(['Date', 'Time', 'Glucose Level (mg/dL)'])
        glucose_records = GlucoseRecord.query.filter_by(user_id=self.user_id).order_by(
            GlucoseRecord.date.desc(),
            GlucoseRecord.time.desc()
        ).all()
        if glucose_records:
            for record in glucose_records:
                cw.writerow([
                    record.date,
                    record.time,
                    record.glucose_level
                ])
        else:
            cw.writerow(['No glucose records found.'])

        # Add a blank row for separation
        cw.writerow([])

        # Write Blood Pressure Records
        cw.writerow(['Blood Pressure Levels'])
        cw.writerow(['Date', 'Time', 'Systolic (mm Hg)', 'Diastolic (mm Hg)'])
        blood_pressure_records = BloodPressureRecord.query.filter_by(user_id=self.user_id).order_by(
            BloodPressureRecord.date.desc(),
            BloodPressureRecord.time.desc()
        ).all()
        if blood_pressure_records:
            for record in blood_pressure_records:
                cw.writerow([
                    record.date,
                    record.time,
                    record.systolic,
                    record.diastolic
                ])
        else:
            cw.writerow(['No blood pressure records found.'])

        # Generate the CSV data
        output = io.BytesIO()
        output.write(si.getvalue().encode('utf-8'))
        output.seek(0)

        return output


    def generate_pdf_report(self):
        """
        Generate PDF data for the user's health records.
        """
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Define margins and line height
        top_margin = 50
        bottom_margin = 50
        left_margin = 50
        right_margin = 50
        line_height = 15  # Adjust as needed

        # Starting position for y
        y = height - top_margin

        # Title
        p.setFont("Helvetica-Bold", 16)
        p.drawString(left_margin, y, "Health Report")
        y -= line_height * 2

        # Report date
        p.setFont("Helvetica", 12)
        p.drawString(left_margin, y, f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        y -= line_height * 2

        # Function to check and handle page breaks
        def check_page_break(y_position, p):
            if y_position < bottom_margin:
                p.showPage()
                p.setFont("Helvetica", 12)  # Reset font after page break
                return height - top_margin
            return y_position

        # Glucose Records
        p.setFont("Helvetica-Bold", 14)
        p.drawString(left_margin, y, "Glucose Levels:")
        y -= line_height * 2
        p.setFont("Helvetica", 12)

        glucose_records = GlucoseRecord.query.filter_by(user_id=self.user_id).order_by(
            GlucoseRecord.date.desc(),
            GlucoseRecord.time.desc()
        ).all()

        if glucose_records:
            for record in glucose_records:
                # Check for page break
                y = check_page_break(y, p)
                p.drawString(left_margin + 20, y, f"Date: {record.date}")  # Removed .strftime
                y -= line_height
                p.drawString(left_margin + 20, y, f"Time: {record.time}")  # Removed .strftime
                y -= line_height
                p.drawString(left_margin + 20, y, f"Glucose Level: {record.glucose_level} mg/dL")
                y -= line_height * 2  # Extra space after each record
        else:
            y = check_page_break(y, p)
            p.drawString(left_margin + 20, y, "No glucose records found.")
            y -= line_height * 2

        # Blood Pressure Records
        y = check_page_break(y, p)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(left_margin, y, "Blood Pressure Levels:")
        y -= line_height * 2
        p.setFont("Helvetica", 12)

        blood_pressure_records = BloodPressureRecord.query.filter_by(user_id=self.user_id).order_by(
            BloodPressureRecord.date.desc(),
            BloodPressureRecord.time.desc()
        ).all()

        if blood_pressure_records:
            for record in blood_pressure_records:
                y = check_page_break(y, p)
                p.drawString(left_margin + 20, y, f"Date: {record.date}")  # Removed .strftime
                y -= line_height
                p.drawString(left_margin + 20, y, f"Time: {record.time}")  # Removed .strftime
                y -= line_height
                p.drawString(left_margin + 20, y, f"Systolic: {record.systolic} mm Hg")
                y -= line_height
                p.drawString(left_margin + 20, y, f"Diastolic: {record.diastolic} mm Hg")
                y -= line_height * 2
        else:
            y = check_page_break(y, p)
            p.drawString(left_margin + 20, y, "No blood pressure records found.")
            y -= line_height * 2

        # Summary Section
        y = check_page_break(y, p)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(left_margin, y, "Summary:")
        y -= line_height * 2
        p.setFont("Helvetica", 12)

        summary_text = (
            "This report contains your logged health data entries, including glucose levels "
            "and blood pressure readings. Please review the data carefully and consult with "
            "your healthcare provider if you have any concerns."
        )

        # Create a text object for the summary
        text_object = p.beginText()
        text_object.setTextOrigin(left_margin, y)
        text_object.setFont("Helvetica", 12)
        text_object.setLeading(line_height)

        # Split the summary text into lines that fit within the page width
        max_width = width - left_margin - right_margin
        words = summary_text.split()
        lines = []
        line = ''

        for word in words:
            test_line = f"{line} {word}" if line else word
            if stringWidth(test_line, "Helvetica", 12) <= max_width:
                line = test_line
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)

        # Add the lines to the text object
        for line in lines:
            y = check_page_break(y - line_height, p)
            text_object.setTextOrigin(left_margin, y)
            text_object.textLine(line)

        p.drawText(text_object)

        p.save()
        buffer.seek(0)

        return buffer