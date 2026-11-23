package finops.cost
import rego.v1

# Yapılandırma data.* altında gelir; testlerde "with data.<anahtar> as ..." kullanılır.

test_under_limit_passes if {
	count(deny) == 0 with input as {"totalMonthlyCost": "11.0", "pastTotalMonthlyCost": "11.0"}
}

test_over_limit_denied if {
	count(deny) == 1 with input as {"totalMonthlyCost": "245.0", "pastTotalMonthlyCost": "11.0"}
}

test_exact_limit_passes if {
	count(deny) == 0 with input as {"totalMonthlyCost": "30", "pastTotalMonthlyCost": "0"}
}

test_near_limit_warns_not_denies if {
	count(deny) == 0 with input as {"totalMonthlyCost": "25", "pastTotalMonthlyCost": "10"}
	count(warn) == 1 with input as {"totalMonthlyCost": "25", "pastTotalMonthlyCost": "10"}
}

test_warn_mode_downgrades_to_warn if {
	count(deny) == 0 with input as {"totalMonthlyCost": "245"}
		with data.budget as {"mode": "warn"}
	count(warn) == 1 with input as {"totalMonthlyCost": "245"}
		with data.budget as {"mode": "warn"}
}

test_budget_overrides_profile if {
	count(deny) == 0 with input as {"totalMonthlyCost": "90"}
		with data.budget as {"monthly_usd": 100}
	count(deny) == 1 with input as {"totalMonthlyCost": "120"}
		with data.budget as {"monthly_usd": 100}
}

test_environment_overrides_budget if {
	count(deny) == 0 with input as {"totalMonthlyCost": "300"}
		with data.environment as "prod"
		with data.budget as {"monthly_usd": 30, "mode": "block"}
		with data.environments as {"prod": {"monthly_usd": 400, "mode": "warn"}}
	count(warn) == 1 with input as {"totalMonthlyCost": "500"}
		with data.environment as "prod"
		with data.budget as {"monthly_usd": 30, "mode": "block"}
		with data.environments as {"prod": {"monthly_usd": 400, "mode": "warn"}}
}

test_startup_profile_defaults if {
	count(deny) == 0 with input as {"totalMonthlyCost": "100"} with data.profile as "startup"
	count(deny) == 1 with input as {"totalMonthlyCost": "200"} with data.profile as "startup"
}

test_unknown_profile_falls_back_to_solo if {
	count(deny) == 1 with input as {"totalMonthlyCost": "50"} with data.profile as "bilinmeyen"
}

test_no_config_uses_safe_defaults if {
	count(deny) == 1 with input as {"totalMonthlyCost": "50"}
}

test_increase_percent_rule if {
	count(warn) == 0 with input as {"totalMonthlyCost": "110", "pastTotalMonthlyCost": "100"}
		with data.profile as "enterprise"
		with data.rules as {"max_increase_percent": 20}

	# enterprise varsayılanı warn modu: ihlal warn olarak çıkar
	count(warn) == 1 with input as {"totalMonthlyCost": "150", "pastTotalMonthlyCost": "100"}
		with data.profile as "enterprise"
		with data.rules as {"max_increase_percent": 20}
}

test_increase_percent_blocks_in_block_mode if {
	count(deny) == 1 with input as {"totalMonthlyCost": "28", "pastTotalMonthlyCost": "10"}
		with data.rules as {"max_increase_percent": 50}
}

test_increase_rule_disabled_by_default if {
	count(deny) == 0 with input as {"totalMonthlyCost": "20", "pastTotalMonthlyCost": "1"}
}

test_missing_cost_fails_closed if {
	count(deny) == 1 with input as {}
}

test_null_cost_fails_closed if {
	count(deny) == 1 with input as {"totalMonthlyCost": null}
}

test_garbage_cost_fails_closed if {
	count(deny) == 1 with input as {"totalMonthlyCost": "abc"}
}

test_numeric_cost_supported if {
	count(deny) == 1 with input as {"totalMonthlyCost": 245}
}