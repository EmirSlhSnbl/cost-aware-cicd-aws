package cost.budget_test

import rego.v1

test_deny_when_over_budget if {
	count(data.cost.budget.deny) == 1 with input as {"totalMonthlyCost": "245.0", "diffTotalMonthlyCost": "234.0"}
}

test_no_deny_when_under_budget if {
	count(data.cost.budget.deny) == 0 with input as {"totalMonthlyCost": "10.0", "diffTotalMonthlyCost": "10.0"}
}

test_warn_on_big_increase if {
	count(data.cost.budget.warn) == 1 with input as {"totalMonthlyCost": "30.0", "diffTotalMonthlyCost": "20.0"}
}

test_no_warn_on_small_increase if {
	count(data.cost.budget.warn) == 0 with input as {"totalMonthlyCost": "10.0", "diffTotalMonthlyCost": "10.0"}
}

test_null_cost_is_safe if {
	count(data.cost.budget.deny) == 0 with input as {"totalMonthlyCost": null, "diffTotalMonthlyCost": null}
}