from __future__ import annotations

from pathlib import Path

from lottery_data import (
    backtest_model_ablation,
    backtest_strategies,
    data_freshness_label,
    load_draws,
    run_parameter_sweep,
    run_repeated_backtests,
    save_backtest_run,
    summarise_backtest,
    summarise_match_distribution,
    summarise_repeated_backtests,
    theoretical_expected_matches,
    theoretical_prize_probabilities,
)


OUTPUT_DIR = Path("analysis_outputs")


def main() -> None:
    df = load_draws()
    OUTPUT_DIR.mkdir(exist_ok=True)

    config = {
        "training_window": 300,
        "test_draws": 200,
        "recent_draw_count": 100,
        "simulations": 300,
        "half_life": 75,
        "random_seed": 42,
    }
    results = backtest_strategies(df, **config)
    summary = summarise_backtest(results)
    distribution = summarise_match_distribution(results)
    csv_path, json_path = save_backtest_run(results, output_dir=OUTPUT_DIR, config=config, name="default_backtest")
    summary_path = OUTPUT_DIR / "default_backtest_summary.csv"
    distribution_path = OUTPUT_DIR / "default_match_distribution.csv"
    summary.to_csv(summary_path, index=False)
    distribution.to_csv(distribution_path, index=False)

    repeated = run_repeated_backtests(
        df,
        seeds=list(range(42, 52)),
        training_window=300,
        test_draws=75,
        recent_draw_count=100,
        simulations=100,
        half_life=75,
    )
    repeated_summary = summarise_repeated_backtests(repeated)
    repeated_path = OUTPUT_DIR / "repeated_seed_runs.csv"
    repeated_summary_path = OUTPUT_DIR / "repeated_seed_summary.csv"
    repeated.to_csv(repeated_path, index=False)
    repeated_summary.to_csv(repeated_summary_path, index=False)

    sweep = run_parameter_sweep(
        df,
        half_lives=[25, 75, 150, 250],
        simulation_counts=[100, 300],
        training_windows=[100, 300],
        test_draws=75,
        recent_draw_counts=[50, 100],
        random_seed=42,
    )
    sweep_path = OUTPUT_DIR / "parameter_sweep.csv"
    sweep.to_csv(sweep_path, index=False)

    ablation = backtest_model_ablation(
        df,
        training_window=300,
        test_draws=50,
        simulations=100,
        half_life=75,
        random_seed=42,
    )
    ablation_summary = summarise_backtest(ablation)
    ablation_distribution = summarise_match_distribution(ablation)
    ablation_path = OUTPUT_DIR / "model_ablation_runs.csv"
    ablation_summary_path = OUTPUT_DIR / "model_ablation_summary.csv"
    ablation_distribution_path = OUTPUT_DIR / "model_ablation_distribution.csv"
    ablation.to_csv(ablation_path, index=False)
    ablation_summary.to_csv(ablation_summary_path, index=False)
    ablation_distribution.to_csv(ablation_distribution_path, index=False)

    odds_path = OUTPUT_DIR / "theoretical_prize_probabilities.csv"
    theoretical_prize_probabilities().to_csv(odds_path, index=False)

    expected = theoretical_expected_matches()
    print(data_freshness_label(df))
    print(f"Default backtest rows: {len(results)}")
    print(f"Theoretical random total matches: {expected['total_matches']:.3f}")
    print(f"Saved default run: {csv_path}")
    print(f"Saved default JSON: {json_path}")
    print(f"Saved summary: {summary_path}")
    print(f"Saved match distribution: {distribution_path}")
    print(f"Saved repeated-seed summary: {repeated_summary_path}")
    print(f"Saved parameter sweep: {sweep_path}")
    print(f"Saved model ablation summary: {ablation_summary_path}")
    print(f"Saved theoretical prize probabilities: {odds_path}")


if __name__ == "__main__":
    main()
