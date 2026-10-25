package cost.budget

import rego.v1

# Dev ortami icin aylik butce tavani ve tek PR'da kabul edilen artis (USD).
monthly_budget_usd := 30

warn_increase_usd := 15

total := to_number(input.totalMonthlyCost)

increase := to_number(input.diffTotalMonthlyCost)

deny contains msg if {
	total > monthly_budget_usd
	msg := sprintf("Estimated monthly cost $%.2f exceeds the budget of $%d", [total, monthly_budget_usd])
}

warn contains msg if {
	increase > warn_increase_usd
	msg := sprintf("This change increases the monthly cost by $%.2f (warning threshold $%d)", [increase, warn_increase_usd])
}