# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class HrPayslipRun(models.Model):
    _name = "hr.payslip.run"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Payslip Batches"
    _order = "id desc"

    name = fields.Char(required=True, readonly=True)
    slip_ids = fields.One2many(
        "hr.payslip",
        "payslip_run_id",
        string="Payslips",
        readonly=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("close", "Close")],
        string="Status",
        index=True,
        readonly=True,
        copy=False,
        tracking=1,
        default="draft",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        copy=False,
        default=lambda self: self.env.company,
    )
    date_start = fields.Date(
        string="Date From",
        required=True,
        readonly=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    date_end = fields.Date(
        string="Date To",
        required=True,
        readonly=True,
        default=lambda self: fields.Date.today().replace(day=1)
        + relativedelta(months=+1, day=1, days=-1),
    )
    credit_note = fields.Boolean(
        readonly=True,
        help="If its checked, indicates that all payslips generated from here "
        "are refund payslips.",
    )
    struct_id = fields.Many2one(
        "hr.payroll.structure",
        string="Structure",
        readonly=True,
        help="Defines the rules that have to be applied to this payslip batch, "
        "accordingly to the contract chosen. If you let empty the field "
        "contract, this field isn't mandatory anymore and thus the rules "
        "applied will be all the rules set on the structure of all contracts "
        "of the employee valid for the chosen period",
    )
    # Total to expense
    total_amount = fields.Float(string="Total Salary", compute="_compute_total_salary", store=True)
    billed = fields.Boolean(default=False)

    @api.depends('slip_ids')
    @api.onchange('slip_ids')
    def _compute_total_salary(self):
        for rec in self:
            if rec.slip_ids:
                total = rec.slip_ids.mapped('net_salary')
                rec.total_amount = sum(total)


    def draft_payslip_run(self):
        return self.write({"state": "draft"})

    def close_payslip_run(self):
        if not self.billed:
            raise ValidationError(f"Create an expense bill for this salary run.")
        return self.write({"state": "close"})


    def action_create_expense(self):
        """Create an expense record for this payslip batch"""
        expense_obj = self.env["hr.expense"]

        for batch in self:
            if not batch.total_amount:
                raise ValidationError(f"Cannot create expense: total salary is {batch.total_amount}.")

            expense_vals = {
                "name": f"Salary Expense - {batch.name}",
                "employee_id": self.env.user.employee_id.id,  # Linked to current user's employee
                "unit_amount": batch.total_amount,
                "quantity": 1,
                "payslip_run_id": batch.id,
                "company_id": batch.company_id.id,
                "currency_id": batch.company_id.currency_id.id,
            }

            expense = expense_obj.create(expense_vals)
            batch.billed = True

        return expense


class HrExpense(models.Model):
    _inherit = "hr.expense"

    payslip_run_id = fields.Many2one(
        "hr.payslip.run",
        string="Payslip Batch",
        help="Link this expense to a payslip batch"
    )

