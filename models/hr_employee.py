# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class EmployeeLoanManager(models.Model):
    _name = "employee.loan"
    _description = "all employee loan from company"

    name = fields.Date(string="Date", default=fields.Date.today)
    amount = fields.Float(digits="Payroll", string="amount")
    paid = fields.Boolean(string="Paid")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    tag_status = fields.Char(
        string="Tag",
        compute="_compute_tag_status",
        store=False
    )

    def _compute_tag_status(self):
        for loan in self:
            loan.tag_status = "Paid" if loan.paid else "Not Paid"

    def action_mark_loan_as_paid(self):
        self.paid = True
        self.employee_id.compute_total_loan_amount()
        

    @api.model
    def create(self, vals):
        res = super(EmployeeLoanManager, self).create(vals)
        res.employee_id.compute_total_loan_amount()
        return res

    def write(self, vals):
        # set new amount
        res = super(EmployeeLoanManager, self).write(vals)
        self.employee_id.compute_total_loan_amount()
        return res

    def unlink(self):
        for record in self:
            record.employee_id.compute_total_loan_amount()
        return super(EmployeeLoanManager, self).unlink()


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    _description = "Employee"

    slip_ids = fields.One2many(
        "hr.payslip", "employee_id", string="Payslips", readonly=True
    )
    payslip_count = fields.Integer(
        compute="_compute_payslip_count",
        groups="payroll.group_payroll_user",
    )
    loan_amount = fields.Float(string="Total Loan")


    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.slip_ids)


    def compute_total_loan_amount(self):
        """Compute total loan amounts based on related loan records"""

        # Calculate total outstanding loans (unpaid)
        loan_ids = self.env['employee.loan'].search([('employee_id', '=', self.id), ('paid', '=', False)])
        # raise ValidationError(f"{loan_ids}")
        outstanding_loan_amount = loan_ids.mapped('amount')
        self.loan_amount = sum(outstanding_loan_amount)
        return True
