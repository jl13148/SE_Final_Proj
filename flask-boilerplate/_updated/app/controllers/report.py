from flask import Blueprint, render_template, redirect, url_for, send_file, flash
from flask_login import login_required, current_user
from datetime import datetime
from app.services.report_service import ReportService
from app.extensions import db

report = Blueprint('report', __name__)

@report.route('/health-reports', methods=['GET', 'POST'])
@login_required
def health_reports():
    return render_template('pages/health_reports.html')

@report.route('/export/csv', methods=['POST'])
@login_required
def export_csv():
    try:
        report_service = ReportService(db, current_user.id)
        output = report_service.generate_csv_report()

        csv_filename = f"health_report_{datetime.now().strftime('%Y%m%d')}.csv"

        return send_file(
            output,
            as_attachment=True,
            download_name=csv_filename,
            mimetype='text/csv'
        )
    except Exception as e:
        flash(f'Error exporting CSV: {str(e)}', 'danger')
        return redirect(url_for('report.health_reports'))

@report.route('/export/pdf', methods=['POST'])
@login_required
def export_pdf():
    try:
        report_service = ReportService(db, current_user.id)
        buffer = report_service.generate_pdf_report()

        pdf_filename = f"health_report_{datetime.now().strftime('%Y%m%d')}.pdf"

        return send_file(
            buffer,
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'Error generating PDF report: {str(e)}', 'danger')
        return redirect(url_for('report.health_reports'))