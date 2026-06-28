#!/usr/bin/env python
# coding: utf-8

import streamlit as st
from sklearn.cluster import KMeans
from sklearn.preprocessing import MultiLabelBinarizer

from lottery_data import (
    backtest_model_ablation,
    backtest_strategies,
    data_freshness_label,
    ensure_backtest_schema,
    filter_recent_draws,
    generate_balanced_ticket,
    generate_ranked_tickets,
    generate_ticket,
    get_cold_numbers,
    get_top_numbers,
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


CACHE_SCHEMA_VERSION = 2


@st.cache_data
def load_data():
    return load_draws()


@st.cache_data
def cluster_draws(df, n_clusters=5):
    clustered = df.copy()
    mlb = MultiLabelBinarizer()
    X = mlb.fit_transform(clustered["Balls"])
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clustered["Cluster"] = kmeans.fit_predict(X)
    return clustered


df = load_data()
df_clustered = cluster_draws(df)

st.sidebar.title("Millionaire Predictor")
recent_draw_count = st.sidebar.slider("Recent draw window", min_value=25, max_value=250, value=100, step=25)

st.title("EuroMillions Lucky Ticket Generator")
st.caption(data_freshness_label(df))

generator_tab, model_tab, research_tab = st.tabs(["Ticket generator", "Model Lab", "Research Lab"])

with generator_tab:
    mode = st.selectbox(
        "Generation mode",
        ["Cluster hot numbers", "Recent hot numbers", "Cold numbers", "Balanced mix"],
    )
    top_n = st.slider("Candidate pool size", min_value=5, max_value=20, value=10)

    selected_cluster = None
    working_df = df
    candidate_label = ""

    if mode == "Cluster hot numbers":
        selected_cluster = st.selectbox("Choose a cluster", sorted(df_clustered["Cluster"].unique()))
        working_df = df_clustered[df_clustered["Cluster"] == selected_cluster]
        candidates = get_top_numbers(working_df, top_n)
        candidate_label = f"Cluster {selected_cluster} top numbers"
    elif mode == "Recent hot numbers":
        working_df = filter_recent_draws(df, recent_draw_count)
        candidates = get_top_numbers(working_df, top_n)
        candidate_label = f"Top numbers from the latest {len(working_df)} dated draws"
    elif mode == "Cold numbers":
        candidates = get_cold_numbers(df, top_n)
        candidate_label = "Least frequent historical numbers"
    else:
        working_df = filter_recent_draws(df, recent_draw_count)
        candidates = get_top_numbers(working_df, top_n)
        candidate_label = f"Balanced mix using the latest {len(working_df)} dated draws"

    top_balls, top_stars = candidates

    st.subheader(candidate_label)
    st.markdown(f"**Balls:** {[number for number, _ in top_balls]}")
    st.markdown(f"**Lucky Stars:** {[number for number, _ in top_stars]}")

    if st.button("Generate My Lucky Ticket!"):
        if mode == "Balanced mix":
            balls, stars = generate_balanced_ticket(df, recent_draw_count)
        else:
            balls, stars = generate_ticket(candidates)
        st.success(f"Your Lucky Ticket: Balls {balls} | Stars {stars}")


@st.cache_data
def ranked_tickets(data, simulations, half_life, top_k):
    return generate_ranked_tickets(data, simulations=simulations, half_life=half_life, top_k=top_k)


@st.cache_data
def run_backtest(data, training_window, test_draws, recent_window, simulations, half_life, schema_version):
    return ensure_backtest_schema(
        backtest_strategies(
            data,
            training_window=training_window,
            test_draws=test_draws,
            recent_draw_count=recent_window,
            simulations=simulations,
            half_life=half_life,
        )
    )


@st.cache_data
def run_sweep(
    data,
    half_lives,
    simulation_counts,
    training_windows,
    test_draws,
    recent_windows,
    random_seed,
    schema_version,
):
    return run_parameter_sweep(
        data,
        half_lives=list(half_lives),
        simulation_counts=list(simulation_counts),
        training_windows=list(training_windows),
        test_draws=test_draws,
        recent_draw_counts=list(recent_windows),
        random_seed=random_seed,
    )


@st.cache_data
def run_repeated(data, seed_count, training_window, test_draws, recent_window, simulations, half_life, schema_version):
    return run_repeated_backtests(
        data,
        seeds=list(range(42, 42 + seed_count)),
        training_window=training_window,
        test_draws=test_draws,
        recent_draw_count=recent_window,
        simulations=simulations,
        half_life=half_life,
    )


@st.cache_data
def run_ablation(data, training_window, test_draws, simulations, half_life, schema_version):
    return ensure_backtest_schema(
        backtest_model_ablation(
            data,
            training_window=training_window,
            test_draws=test_draws,
            simulations=simulations,
            half_life=half_life,
        )
    )


with model_tab:
    st.subheader("Ranked ticket model")
    half_life = st.slider("Recency half-life", min_value=25, max_value=250, value=75, step=25)
    simulations = st.slider("Monte Carlo candidates", min_value=250, max_value=5000, value=1000, step=250)
    top_k = st.slider("Ranked tickets to show", min_value=3, max_value=10, value=5)

    tickets = ranked_tickets(df, simulations, half_life, top_k)
    ticket_rows = [
        {
            "Rank": rank,
            "Balls": ticket.balls,
            "Lucky Stars": ticket.stars,
            "Score": round(ticket.score, 3),
            "Hot": round(ticket.hot_score, 3),
            "Cold": round(ticket.cold_score, 3),
            "Balance": round(ticket.balance_score, 3),
            "Spread": round(ticket.spread_score, 3),
            "Pairs": round(ticket.pair_score, 3),
        }
        for rank, ticket in enumerate(tickets, start=1)
    ]
    st.dataframe(ticket_rows, use_container_width=True, hide_index=True)

    st.subheader("Walk-forward backtest")
    test_draws = st.slider("Test draw count", min_value=50, max_value=500, value=200, step=50)
    training_window = st.slider("Minimum training draws", min_value=100, max_value=800, value=300, step=50)
    backtest_simulations = st.slider("Backtest candidates per draw", min_value=100, max_value=1000, value=300, step=100)

    results = run_backtest(
        df,
        training_window,
        test_draws,
        recent_draw_count,
        backtest_simulations,
        half_life,
        CACHE_SCHEMA_VERSION,
    )
    summary = summarise_backtest(results)
    for column in [
        "avg_ball_matches",
        "avg_star_matches",
        "avg_total_matches",
        "total_ci_low",
        "total_ci_high",
        "prize_hit_rate",
        "hit_ci_low",
        "hit_ci_high",
    ]:
        summary[column] = summary[column].round(3)

    st.dataframe(summary, use_container_width=True, hide_index=True)

    tier_counts = (
        results[results["Prize hit"]]
        .groupby(["Strategy", "Prize tier"])
        .size()
        .reset_index(name="Hits")
        .sort_values(["Strategy", "Hits"], ascending=[True, False])
    )
    with st.expander("Prize-tier hit distribution"):
        st.dataframe(tier_counts, use_container_width=True, hide_index=True)

    with st.expander("Total-match distribution"):
        match_distribution = summarise_match_distribution(results).copy()
        for column in ["match_0_rate", "match_1_rate", "match_2_rate", "match_3_plus_rate", "total_match_std"]:
            match_distribution[column] = match_distribution[column].round(3)
        st.dataframe(match_distribution, use_container_width=True, hide_index=True)

    expected = theoretical_expected_matches()
    st.metric("Theoretical random expected matches", round(expected["total_matches"], 3))
    with st.expander("Theoretical prize-tier odds"):
        odds = theoretical_prize_probabilities().copy()
        odds["Probability"] = odds["Probability"].map(lambda value: f"{value:.10f}")
        odds["Odds 1 in"] = odds["Odds 1 in"].round(0).astype(int)
        st.dataframe(odds.drop(columns=["Tier rank"]), use_container_width=True, hide_index=True)

    config = {
        "training_window": training_window,
        "test_draws": test_draws,
        "recent_draw_count": recent_draw_count,
        "simulations": backtest_simulations,
        "half_life": half_life,
    }
    if st.button("Save this backtest run"):
        csv_path, json_path = save_backtest_run(results, config=config)
        st.success(f"Saved CSV to {csv_path} and JSON to {json_path}")

    st.caption("Backtesting uses only draws before each tested date. It is a strategy comparison, not a promise of predictability.")


with research_tab:
    st.subheader("Repeated-seed robustness")
    seed_count = st.slider("Number of seeds", min_value=3, max_value=20, value=5, step=1)
    robustness_draws = st.slider("Robustness test draw count", min_value=25, max_value=200, value=75, step=25)
    robustness_simulations = st.slider("Robustness candidates per draw", min_value=50, max_value=500, value=100, step=50)

    repeated = run_repeated(
        df,
        seed_count,
        training_window=300,
        test_draws=robustness_draws,
        recent_window=recent_draw_count,
        simulations=robustness_simulations,
        half_life=75,
        schema_version=CACHE_SCHEMA_VERSION,
    )
    repeated_summary = summarise_repeated_backtests(repeated)
    for column in [
        "mean_total_matches",
        "total_ci_low",
        "total_ci_high",
        "mean_prize_hit_rate",
        "hit_ci_low",
        "hit_ci_high",
        "win_rate_vs_random",
        "avg_total_edge_vs_random",
        "avg_hit_edge_vs_random",
    ]:
        if column in repeated_summary.columns:
            repeated_summary[column] = repeated_summary[column].round(3)

    st.dataframe(repeated_summary, use_container_width=True, hide_index=True)

    st.subheader("Model ablation")
    ablation_draws = st.slider("Ablation test draw count", min_value=25, max_value=150, value=50, step=25)
    ablation_simulations = st.slider("Ablation candidates per draw", min_value=50, max_value=300, value=100, step=50)
    ablation = run_ablation(
        df,
        training_window=300,
        test_draws=ablation_draws,
        simulations=ablation_simulations,
        half_life=75,
        schema_version=CACHE_SCHEMA_VERSION,
    )
    ablation_summary = summarise_backtest(ablation)
    ablation_distribution = summarise_match_distribution(ablation)
    ablation_display = ablation_summary.merge(ablation_distribution, on=["Strategy", "draws"], how="left")
    for column in [
        "avg_ball_matches",
        "avg_star_matches",
        "avg_total_matches",
        "total_ci_low",
        "total_ci_high",
        "prize_hit_rate",
        "hit_ci_low",
        "hit_ci_high",
        "match_0_rate",
        "match_1_rate",
        "match_2_rate",
        "match_3_plus_rate",
        "total_match_std",
    ]:
        if column in ablation_display.columns:
            ablation_display[column] = ablation_display[column].round(3)
    st.dataframe(ablation_display, use_container_width=True, hide_index=True)

    st.subheader("Parameter sweep")
    half_life_options = st.multiselect(
        "Half-lives to test",
        options=[25, 50, 75, 100, 150, 200, 250],
        default=[50, 75, 100],
    )
    simulation_options = st.multiselect(
        "Candidate counts to test",
        options=[100, 200, 300, 500, 750, 1000, 3000],
        default=[100, 300],
    )
    recent_window_options = st.multiselect(
        "Recent windows to test",
        options=[25, 50, 100, 150, 250],
        default=[50, 100],
    )
    training_window_options = st.multiselect(
        "Training windows to test",
        options=[100, 300, 500, 800],
        default=[300],
    )
    sweep_test_draws = st.slider("Sweep test draw count", min_value=25, max_value=250, value=75, step=25)
    sweep_seed = st.number_input("Sweep random seed", min_value=1, max_value=9999, value=42, step=1)

    if half_life_options and simulation_options and recent_window_options and training_window_options:
        sweep = run_sweep(
            df,
            tuple(half_life_options),
            tuple(simulation_options),
            tuple(training_window_options),
            sweep_test_draws,
            tuple(recent_window_options),
            int(sweep_seed),
            CACHE_SCHEMA_VERSION,
        )
        display_sweep = sweep.copy()
        for column in [
            "avg_total_matches",
            "total_ci_low",
            "total_ci_high",
            "prize_hit_rate",
            "hit_ci_low",
            "hit_ci_high",
            "match_0_rate",
            "match_1_rate",
            "match_2_rate",
            "match_3_plus_rate",
            "total_match_std",
        ]:
            if column in display_sweep.columns:
                display_sweep[column] = display_sweep[column].round(3)

        st.dataframe(display_sweep, use_container_width=True, hide_index=True)
        chart_source = sweep[
            (sweep["training_window"] == sweep["training_window"].min())
            & (sweep["recent_draw_count"] == sweep["recent_draw_count"].min())
        ]
        hit_rate_chart = chart_source.pivot(index="half_life", columns="simulations", values="prize_hit_rate")
        match_chart = chart_source.pivot(index="half_life", columns="simulations", values="avg_total_matches")
        st.line_chart(hit_rate_chart, use_container_width=True)
        st.line_chart(match_chart, use_container_width=True)
    else:
        st.info("Choose at least one value for each sweep dimension.")
