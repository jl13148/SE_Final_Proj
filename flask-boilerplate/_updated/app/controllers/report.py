from flask import Blueprint, render_template, redirect, url_for, send_file, flash, current_app as app
from flask_login import login_required, current_user
from app.forms import ExportPDFForm, ExportCSVForm
from app.models import GlucoseRecord, BloodPressureRecord
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import csv
from datetime import datetime


report = Blueprint('report', __name__)

@report.route('/health-reports', methods=['GET', 'POST'])
@login_required
def health_reports():
    pdf_form = ExportPDFForm()
    csv_form = ExportCSVForm()
    
    if pdf_form.validate_on_submit() and pdf_form.submit.data:
        return redirect(url_for('export_pdf'))
    if csv_form.validate_on_submit() and csv_form.submit.data:
        return redirect(url_for('export_csv'))
    
    return render_template('pages/health_reports.html', pdf_form=pdf_form, csv_form=csv_form)

@report.route('/export/csv', methods=['POST'])
@login_required
def export_csv():
    try:
        # Create a CSV in memory
        si = io.StringIO()
        cw = csv.writer(si)

        # Write Glucose Records
        cw.writerow(['Glucose Levels'])
        cw.writerow(['Date', 'Time', 'Glucose Level (mg/dL)'])
        glucose_records = GlucoseRecord.query.filter_by(user_id=current_user.id).order_by(GlucoseRecord.date.desc(), GlucoseRecord.time.desc()).all()
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
        blood_pressure_records = BloodPressureRecord.query.filter_by(user_id=current_user.id).order_by(BloodPressureRecord.date.desc(), BloodPressureRecord.time.desc()).all()
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

        # Define the filename with the current date
        csv_filename = f"health_report_{datetime.now().strftime('%Y%m%d')}.csv"

        # Logging the export action
        app.logger.info(f'CSV report exported for user: {current_user.username}')

        return send_file(
            output,
            as_attachment=True,
            download_name=csv_filename,
            mimetype='text/csv'
        )
    except Exception as e:
        app.logger.error(f'Error exporting CSV: {e}')
        flash(f'Error exporting CSV: {str(e)}', 'danger')
        return redirect(url_for('health_reports'))


#----------------------------------------------------------------------------#
# PDF Report Generation Functionality
#----------------------------------------------------------------------------#
@report.route('/export/pdf', methods=['POST'])
@login_required
def export_pdf():
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, height - 50, f"Health Report for {current_user.username}")
        p.setFont("Helvetica", 12)
        p.drawString(100, height - 80, f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        y = height - 120

        glucose_records = GlucoseRecord.query.filter_by(user_id=current_user.id).order_by(
            GlucoseRecord.date.desc(),
            GlucoseRecord.time.desc()
        ).all()
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y, "Glucose Levels:")
        y -= 20
        p.setFont("Helvetica", 12)
        if glucose_records:
            for record in glucose_records:
                if y < 50:
                    p.showPage()
                    y = height - 50
                y -= 20
                p.drawString(120, y, f"Date: {record.date}")
                y -= 20
                p.drawString(120, y, f"Time: {record.time}")
                y -= 20
                p.drawString(120, y, f"Glucose Level: {record.glucose_level} mg/dL")
                y -= 30
        else:
            p.drawString(120, y, "No glucose records found.")
            y -= 20

        y -= 20 
        blood_pressure_records = BloodPressureRecord.query.filter_by(user_id=current_user.id).order_by(
            BloodPressureRecord.date.desc(),
            BloodPressureRecord.time.desc()
        ).all()
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y, "Blood Pressure Levels:")
        y -= 20
        p.setFont("Helvetica", 12)
        if blood_pressure_records:
            for record in blood_pressure_records:
                if y < 50:
                    p.showPage()
                    y = height - 50
                p.drawString(120, y, f"Date: {record.date}")
                y -= 20
                p.drawString(120, y, f"Time: {record.time}")
                y -= 20
                p.drawString(120, y, f"Systolic: {record.systolic} mm/Hg")
                y -= 20
                p.drawString(120, y, f"Diastolic: {record.diastolic} mm/Hg")
                y -= 30 
        else:
            p.drawString(120, y, "No blood pressure records found.")
            y -= 20

        y -= 20
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y, "Summary:")
        y -= 20
        p.setFont("Helvetica", 12)
        summary_text = "This report contains your logged health data entries,\nincluding glucose levels and blood pressure readings."
        text_object = p.beginText(100, y)
        text_object.textLines(summary_text)
        p.drawText(text_object)

        p.showPage()
        p.save()
        buffer.seek(0)

        app.logger.info(f'PDF report exported for user: {current_user.username}')

        return send_file(buffer, as_attachment=True, download_name='health_report.pdf', mimetype='application/pdf')
    except Exception as e:
        app.logger.error(f'Error exporting PDF: {e}')
        flash(f'Error generating PDF report: {str(e)}', 'danger')
        return redirect(url_for('health_reports'))