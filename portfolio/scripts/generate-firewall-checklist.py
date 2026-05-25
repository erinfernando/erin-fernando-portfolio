"""
Generate a one-page Semi-Annual Firewall & Segmentation Review checklist PDF.
Erin Fernando — erinfernando.com
"""
import os
import sys
from fpdf import FPDF

class ChecklistPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.set_auto_page_break(auto=False)

    def header_block(self):
        # Navy header bar
        self.set_fill_color(26, 82, 118)
        self.rect(0, 0, 215.9, 28, 'F')

        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(12, 6)
        self.cell(0, 8, 'Semi-Annual Firewall & Segmentation Review', ln=True)

        self.set_font('Helvetica', '', 9)
        self.set_text_color(174, 214, 241)
        self.set_xy(12, 16)
        self.cell(0, 5, 'PCI DSS 4.0  |  Required every 6 months  |  One-page checklist', ln=True)

    def info_fields(self):
        y = 34
        self.set_text_color(60, 60, 60)
        self.set_font('Helvetica', '', 9)

        fields = [
            ('Business Name:', 90),
            ('Reviewer:', 90),
        ]
        fields_row2 = [
            ('Review Date:', 55),
            ('Review Period:', 55),
        ]

        # Row 1
        x = 12
        for label, width in fields:
            self.set_xy(x, y)
            self.set_font('Helvetica', 'B', 9)
            self.cell(self.get_string_width(label) + 2, 5, label)
            lw = self.get_string_width(label) + 2
            self.set_draw_color(180, 180, 180)
            self.line(x + lw, y + 5, x + width, y + 5)
            x += width + 8

        # Row 2
        y += 10
        x = 12
        for label, width in fields_row2:
            self.set_xy(x, y)
            self.set_font('Helvetica', 'B', 9)
            self.cell(self.get_string_width(label) + 2, 5, label)
            lw = self.get_string_width(label) + 2
            self.line(x + lw, y + 5, x + width, y + 5)
            x += width + 8

        # Suggested schedule note
        self.set_xy(x + 4, y)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, '(Suggested: January + July)')

        return y + 14

    def section_header(self, y, title, color_rgb):
        self.set_fill_color(*color_rgb)
        self.rect(12, y, 191.9, 7, 'F')
        self.set_xy(14, y + 1)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(255, 255, 255)
        self.cell(0, 5, title)
        return y + 9

    def checkbox_item(self, y, text, indent=12):
        self.set_text_color(40, 40, 40)
        self.set_draw_color(160, 160, 160)

        # Checkbox
        box_x = indent + 1
        box_y = y + 0.5
        self.rect(box_x, box_y, 4, 4)

        # Text
        self.set_xy(indent + 8, y)
        self.set_font('Helvetica', '', 9)
        self.multi_cell(180, 4.5, text)
        return self.get_y() + 1.5

    def notes_area(self, y, label, height=14):
        self.set_xy(12, y)
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 4, label)
        y += 5
        self.set_draw_color(200, 200, 200)
        self.rect(12, y, 191.9, height)
        # Light ruled lines
        self.set_draw_color(230, 230, 230)
        for ly in range(int(y + 5), int(y + height), 5):
            self.line(14, ly, 201.9, ly)
        return y + height + 2

    def footer_block(self):
        y = 258
        self.set_draw_color(200, 200, 200)
        self.line(12, y, 203.9, y)

        y += 3
        # Signature lines
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(80, 80, 80)

        self.set_xy(12, y)
        self.cell(30, 4, 'Reviewed by:')
        self.line(42, y + 4, 105, y + 4)

        self.set_xy(112, y)
        self.cell(15, 4, 'Date:')
        self.line(127, y + 4, 175, y + 4)

        # Attribution
        y += 10
        self.set_font('Helvetica', '', 7)
        self.set_text_color(150, 150, 150)
        self.set_xy(12, y)
        self.cell(0, 3, 'Erin Fernando  |  erinfernando.com  |  PCI DSS 4.0 Compliance Template', align='C')


def build_checklist():
    pdf = ChecklistPDF()
    pdf.add_page()
    pdf.header_block()
    y = pdf.info_fields()

    # Section 1: Firewall Rules
    y = pdf.section_header(y, 'FIREWALL RULES', (26, 82, 118))
    items_fw = [
        'Review all active firewall rules. Remove any rules no longer needed.',
        'Confirm inbound rules only allow traffic required for the cardholder data environment (CDE).',
        'Confirm outbound rules restrict CDE traffic to payment processor endpoints only.',
        'Verify default-deny is in place (block everything not explicitly allowed).',
        'Check for any "permit all" or overly broad rules and remove them.',
        'Confirm remote management access (if enabled) requires MFA and encrypted connection.',
    ]
    for item in items_fw:
        y = pdf.checkbox_item(y, item)

    y += 1

    # Section 2: VLAN / Segmentation
    y = pdf.section_header(y, 'VLAN & NETWORK SEGMENTATION', (30, 132, 73))
    items_vlan = [
        'Verify POS / payment devices are on their designated VLAN and cannot reach other VLANs.',
        'Confirm no new devices have been connected to the CDE VLAN since last review.',
        'Test isolation: attempt to ping or access CDE devices from a non-CDE VLAN.',
        'Verify guest Wi-Fi, cameras, and office devices remain on separate VLANs.',
        'Review DHCP leases or static assignments for unexpected devices on the CDE VLAN.',
    ]
    for item in items_vlan:
        y = pdf.checkbox_item(y, item)

    y += 1

    # Section 3: Documentation
    y = pdf.section_header(y, 'DOCUMENTATION & FOLLOW-UP', (44, 62, 80))
    items_doc = [
        'Update the network diagram if any changes were found.',
        'Update the CDE scoping document (list of all in-scope systems).',
        'Log any findings or changes made during this review.',
        'Schedule the next review date (6 months from today).',
    ]
    for item in items_doc:
        y = pdf.checkbox_item(y, item)

    # Notes
    y += 1
    y = pdf.notes_area(y, 'FINDINGS / NOTES:', height=16)

    # Footer
    pdf.footer_block()

    return pdf


if __name__ == '__main__':
    output_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(output_dir, 'pci-firewall-review-checklist.pdf')

    pdf = build_checklist()
    pdf.output(output_path)
    print(f'Generated: {output_path}')
