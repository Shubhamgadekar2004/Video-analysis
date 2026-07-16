import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class ENFReportGenerator:
    def __init__(self, output_path):
        self.output_path = output_path
        self.styles = getSampleStyleSheet()
        
        # Create custom styles
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=15
        )
        
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=25
        )
        
        self.heading2_style = ParagraphStyle(
            'CustomH2',
            parent=self.styles['Heading2'],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#0f172a'),
            spaceBefore=12,
            spaceAfter=8
        )
        
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155'),
            spaceAfter=8
        )
        
        self.callout_style = ParagraphStyle(
            'CustomCallout',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#0f172a'),
            backColor=colors.HexColor('#f1f5f9'),
            borderColor=colors.HexColor('#cbd5e1'),
            borderWidth=1,
            borderPadding=10,
            spaceAfter=15
        )

    def generate_report(self, case_id, filename, metadata, analysis_params, auth_results, tampering_results, plot_paths=None):
        """
        Assembles a PDF report.
        """
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=letter,
            rightMargin=54, leftMargin=54,
            topMargin=54, bottomMargin=54
        )
        
        story = []
        
        # Title Header
        story.append(Paragraph("ENF Forensic Analysis Report", self.title_style))
        story.append(Paragraph(f"Case ID: {case_id}  |  Generated on: 2026-07-16  |  Developer: Shubham", self.subtitle_style))
        story.append(Spacer(1, 10))
        
        # 1. Summary Box
        risk_score = tampering_results.get("risk_score", 0.0)
        risk_percent = int(risk_score * 100)
        
        matched = auth_results.get("matched", False)
        status_text = "AUTHENTIC" if (matched and risk_score < 0.3) else "TAMPERED / SUSPICIOUS" if risk_score >= 0.5 else "UNVERIFIED"
        status_color = "#10b981" if status_text == "AUTHENTIC" else "#ef4444" if status_text == "TAMPERED / SUSPICIOUS" else "#f59e0b"
        
        summary_text = (
            f"<b>Forensic Determination:</b> <font color='{status_color}'><b>{status_text}</b></font><br/>"
            f"<b>Tampering Risk Score:</b> {risk_percent}%<br/>"
            f"<b>Authentication Status:</b> {'Matched against reference database' if matched else 'No database match found'}"
        )
        if matched and auth_results.get("best_time"):
            summary_text += f" (Est. Recording Time: {auth_results.get('best_time')})"
            
        story.append(Paragraph(summary_text, self.callout_style))
        story.append(Spacer(1, 15))
        
        # 2. File & Analysis Metadata
        story.append(Paragraph("File Information", self.heading2_style))
        meta_data = [
            [Paragraph("<b>Filename:</b>", self.body_style), Paragraph(filename, self.body_style)],
            [Paragraph("<b>File Size / Duration:</b>", self.body_style), Paragraph(f"{metadata.get('duration', 0):.2f} seconds", self.body_style)],
            [Paragraph("<b>Resolution / Frame Rate:</b>", self.body_style), Paragraph(f"{metadata.get('width', 0)}x{metadata.get('height', 0)} @ {metadata.get('frame_rate', 0):.2f} fps", self.body_style)],
            [Paragraph("<b>Luminance Source:</b>", self.body_style), Paragraph(analysis_params.get("enf_source", "video").upper(), self.body_style)],
            [Paragraph("<b>Nominal Grid Frequency:</b>", self.body_style), Paragraph(f"{analysis_params.get('nominal_freq', 50)} Hz", self.body_style)]
        ]
        t = Table(meta_data, colWidths=[2.0*inch, 4.0*inch])
        t.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(t)
        story.append(Spacer(1, 20))
        
        # 3. Authentication & Database Alignment
        story.append(Paragraph("Authentication & Correlation Analysis", self.heading2_style))
        auth_text = (
            f"The extracted ENF signal was cross-correlated against the reference grid database. "
            f"A peak cross-correlation coefficient of <b>{auth_results.get('max_correlation', 0):.4f}</b> was obtained. "
        )
        if matched:
            auth_text += (
                f"This exceeds the authentication threshold, confirming a match. "
                f"The estimated date/time of recording is <b>{auth_results.get('best_time')}</b>."
            )
        else:
            auth_text += "This did not meet the threshold for a valid lock, indicating either the recording occurred outside the database coverage period, or the grid frequency signal is too degraded."
            
        story.append(Paragraph(auth_text, self.body_style))
        story.append(Spacer(1, 10))
        
        # Add alignment plot
        if plot_paths and plot_paths.get("comparison"):
            story.append(Image(plot_paths["comparison"], width=6.5*inch, height=2.8*inch))
            story.append(Spacer(1, 20))
            
        # 4. Tampering & Integrity Analysis
        story.append(Paragraph("Integrity & Tampering Detection", self.heading2_style))
        
        discons = tampering_results.get("discontinuities", [])
        splicing = tampering_results.get("splicing_analysis", {})
        
        tamp_text = "No severe anomalies or frequency discontinuities were detected in the ENF signature."
        if discons or (splicing and splicing.get("spliced")):
            tamp_text = "<b>WARNING:</b> Anomalies detected. "
            if discons:
                tamp_text += f"Found {len(discons)} sudden frequency jump(s) which typically indicates cut edits. "
            if splicing and splicing.get("spliced"):
                tamp_text += "Segment-wise cross-correlation indicates inconsistent grid alignments across different sections of the video, which is a strong signature of splicing."
                
        story.append(Paragraph(tamp_text, self.body_style))
        story.append(Spacer(1, 10))
        
        # List discontinuities if any
        if discons:
            discon_data = [[Paragraph("<b>Time (sec)</b>", self.body_style), Paragraph("<b>Jump Size (Hz)</b>", self.body_style), Paragraph("<b>Severity</b>", self.body_style)]]
            for d in discons:
                discon_data.append([
                    Paragraph(f"{d['time']:.2f}", self.body_style),
                    Paragraph(f"{d['jump_hz']:.4f}", self.body_style),
                    Paragraph(f"{int(d['severity']*100)}%", self.body_style)
                ])
            dt = Table(discon_data, colWidths=[2.0*inch, 2.0*inch, 2.0*inch])
            dt.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(dt)
            story.append(Spacer(1, 15))
            
        # Add spectrogram/correlation plots
        if plot_paths and plot_paths.get("spectrogram"):
            story.append(Image(plot_paths["spectrogram"], width=6.5*inch, height=2.6*inch))
            
        # Add signature / developer block at the bottom
        story.append(Spacer(1, 20))
        footer_style = ParagraphStyle(
            'ReportFooter',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#94a3b8'),
            alignment=1  # Centered
        )
        story.append(Paragraph("This report was generated using the ENF Shield Forensic Platform developed by Shubham.", footer_style))
        
        # Build PDF
        doc.build(story)
        return self.output_path
