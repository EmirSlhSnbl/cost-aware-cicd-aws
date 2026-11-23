package finops.cost
import rego.v1

# Öncelik: environments[ortam] > budget > profil > yerleşik varsayılan
profiles := {
	"solo": {"monthly_usd": 30, "mode": "block"},
	"startup": {"monthly_usd": 150, "mode": "block"},
	"enterprise": {"monthly_usd": 1000, "mode": "warn"},
}

default profile_name := "solo"

profile_name := data.profile

base := object.get(profiles, profile_name, profiles.solo)

default env_name := "dev"

env_name := data.environment

default env_cfg := {}

env_cfg := data.environments[env_name]

default budget_cfg := {}

budget_cfg := data.budget

limit := object.get(env_cfg, "monthly_usd", object.get(budget_cfg, "monthly_usd", base.monthly_usd))

mode := object.get(env_cfg, "mode", object.get(budget_cfg, "mode", base.mode))

warn_pct := object.get(budget_cfg, "warn_at_percent", 80)

default max_increase := 0

max_increase := data.rules.max_increase_percent

# --- Infracost çıktısı (fail-closed: okunamazsa reddet) ---
# Not: OPA'da to_number(null) sessizce 0 döner. Bu yüzden türü açıkça denetliyoruz.
total := to_number(input.totalMonthlyCost) if is_string(input.totalMonthlyCost)

total := input.totalMonthlyCost if is_number(input.totalMonthlyCost)

past := to_number(object.get(input, "pastTotalMonthlyCost", "0"))

# --- İhlaller ---
violations contains msg if {
	total > limit
	msg := sprintf(
		"Aylık tahmini maliyet %v $, '%s' ortamı için sınır %v $ (profil: %s)",
		[total, env_name, limit, profile_name],
	)
}

violations contains msg if {
	max_increase > 0
	past > 0
	pct := ((total - past) / past) * 100
	pct > max_increase
	msg := sprintf("Bu PR maliyeti %%%v artırıyor (izin verilen: %%%v)", [round(pct), max_increase])
}

violations contains "Infracost çıktısında totalMonthlyCost okunamadı" if {
	not total
}

# --- Mod: block ise deny, değilse warn ---
deny contains msg if {
	mode == "block"
	some msg in violations
}

warn contains msg if {
	mode != "block"
	some msg in violations
}

# Sınıra yaklaşma uyarısı (ihlal yokken)
warn contains msg if {
	count(violations) == 0
	total > (limit * warn_pct) / 100
	msg := sprintf(
		"Maliyet sınırın %%%v'ine yaklaştı: %v $ / %v $",
		[warn_pct, total, limit],
	)
}