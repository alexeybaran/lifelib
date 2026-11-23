"""Convenience entry point for the Outer reporting Cell."""


def annual_risk_report(model, num_scenarios, annual_steps):
    return model.Outer.annual_risk_report(num_scenarios, annual_steps)
