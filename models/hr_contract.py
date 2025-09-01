# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.exceptions import ValidationError

class HrContract(models.Model):
    """
    Employee contract based on the visa, work permits
    allows to configure different Salary structure
    """

    _inherit = "hr.contract"
    _description = "Employee Contract"

    struct_id = fields.Many2one("hr.payroll.structure", string="Salary Structure")
    schedule_pay = fields.Selection(
        [
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("semi-annually", "Semi-annually"),
            ("annually", "Annually"),
            ("weekly", "Weekly"),
            ("bi-weekly", "Bi-weekly"),
            ("bi-monthly", "Bi-monthly"),
        ],
        string="Scheduled Pay",
        index=True,
        default="monthly",
        help="Defines the frequency of the wage payment.",
    )
    resource_calendar_id = fields.Many2one(
        required=True, help="Employee's working schedule."
    )
    tax = fields.Float(string="Total Tax", compute="_compute_tax")
    is_ssn = fields.Boolean(default=False, string="Pays SNNIT")

    @api.depends('wage', 'is_ssn')
    def _compute_tax(self):
        """Compute tax based on employee salary using PAYE bands"""
        for rec in self:
            if rec.wage:
                gross = rec.wage
                if rec.is_ssn:
                    snnit_amount = rec.wage * 5.5 / 100
                    gross -= snnit_amount
                tax = 0.0
                bands = [
                    (490, 0.0),
                    (110, 0.05),
                    (130, 0.10),
                    (3166.67, 0.175),
                    (16000, 0.25),
                ]
                remaining = gross
                for band_amount, rate in bands:
                    taxable = min(remaining, band_amount)
                    tax += taxable * rate
                    remaining -= taxable
                    if remaining <= 0:
                        break
                # If there is still remaining salary above all bands, tax at 25%
                if remaining > 0:
                    tax += remaining * 0.25
                rec.tax = tax
            else:
                rec.tax = 0.0

    def get_all_structures(self):
        """
        @return: the structures linked to the given contracts, ordered by
                 hierachy (parent=False first, then first level children and
                 so on) and without duplicates
        """
        structures = self.mapped("struct_id")
        if not structures:
            return []
        # YTI TODO return browse records
        return list(set(structures._get_parent_structure().ids))
