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
    billed = fields.Boolean(default=False)
    

    def draft_payslip_run(self):
        return self.write({"state": "draft"})

    # def close_payslip_run(self):
    #     if not self.billed:
    #         raise ValidationError(f"Create an expense bill for this salary run.")
    #     return self.write({"state": "close"})
    

    def action_open_related_expenses(self):
        """Open the related expenses for this payslip batch"""
        return {
            "type": "ir.actions.act_window",
            "name": "Related Expenses",
            "res_model": "hr.expense",
            "domain": [("payslip_run_id", "=", self.id)],
            "view_mode": "tree,form",
            "context": {"create": False},
        }

    def action_create_expense(self):
        """Create an expense record for this payslip batch and close it"""
        expense_obj = self.env["hr.expense"]
        product_obj = self.env["product.product"]

        # process slips to done if not.
        for slip in self.slip_ids:
            if slip.state == "done":
                continue
            else:
                slip.state = "done"

        # find default_code [SLY] 
        product = product_obj.search([('default_code', '=', 'SLY')], limit=1)
        if not product:
            # create product if not found
            new_product = product_obj.create(
                {"name": "Salary Expense", "default_code": "SLY", "type": "service"}
            )
            product = new_product

        for batch in self:
            total_amount = sum(batch.slip_ids.mapped('net_salary'))
            if batch.billed:
                raise ValidationError(f"Expense already created for payslip batch {batch.name}.")
            # if not batch.total_amount:
            #     raise ValidationError(f"Cannot create expense: total salary is {batch.total_amount}.")

            expense_vals = {
                "name": f"Salary Expense - {batch.name}",
                "employee_id": self.env.user.employee_id.id,  # Linked to current user's employee
                "total_amount_currency": total_amount,
                "payslip_run_id": batch.id,
                "company_id": batch.company_id.id,
                "currency_id": batch.company_id.currency_id.id,
                "payment_mode": "company_account",
                "product_id": product.id,
            }

            expense = expense_obj.create(expense_vals)
            expense.action_submit_expenses()
            batch.billed = True
            batch.write({"state": "close"})
            self.env.user.notify_info(message=f"Expense created for payslip batch {batch.name}.")
        return expense


class HrExpense(models.Model):
    _inherit = "hr.expense"

    payslip_run_id = fields.Many2one(
        "hr.payslip.run",
        string="Payslip Batch",
        help="Link this expense to a payslip batch"
    )

