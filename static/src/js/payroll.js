/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class PayrollUI extends Component {
    static props = {
        workingYears: { type: Array, optional: true },
        selectedYearId: { type: Number, optional: true },
        payslips: { type: Array, optional: true },
        loading: { type: Boolean, optional: true },
    };
    
    setup() {
        this.orm = useService("orm");
        this.action = useService('action')
        this.state = useState({
            workingYears: [],
            selectedYearId: null,
            payslips: [],
            loading: true,
        });

        onWillStart(async () => {
            // Get all working years
            const years = await this.orm.searchRead("hr.working_year", [], ["id", "name"]);
            this.state.workingYears = years;
            if (years.length) {
                this.state.selectedYearId = years[0].id;
            }
            await this.loadPayslips();
        });
    }

    async loadPayslips() {
        this.state.loading = true;
        const domain = [
            ["employee_id.user_id", "=", this.env.services.user.userId],
            ["year", "=", this.state.selectedYearId],
            ["state", "=", "done"]
        ];
        const payslips = await this.orm.searchRead("hr.payslip", domain, ["id", "name", "date_from", "date_to"]);
        this.state.payslips = payslips;
        this.state.loading = false;
    }

    async onYearChange(ev) {
        this.state.selectedYearId = parseInt(ev.target.value);
        await this.loadPayslips();
    }

    async onPayslipClick(ev) {
        const payslipId = parseInt(ev.currentTarget.dataset.payslipId);
        
        // Call the action_print_payslip method to generate PDF
        const result = await this.orm.call('hr.payslip', 'action_print_payslip', [payslipId]);
        
        // Execute the returned action (which will open/download the PDF)
        if (result) {
            this.action.doAction(result);
        }
    }
}

PayrollUI.template = "MainPortal";

// Register the action so it can be called from a server action or menu
registry.category("actions").add("payslip_portal", PayrollUI);
