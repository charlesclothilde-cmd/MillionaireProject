#!/usr/bin/env python
# coding: utf-8

import random

import pandas as pd
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.preprocessing import MultiLabelBinarizer

from lottery_data import (
    MODEL_VARIANTS,
    analyse_ticket_behavior,
    backtest_model_ablation,
    backtest_strategies,
    data_freshness_label,
    ensure_backtest_schema,
    generate_anti_crowd_tickets,
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
    summarise_prize_tier_values,
    summarise_repeated_backtests,
    theoretical_expected_matches,
    theoretical_expected_return,
    theoretical_prize_probabilities,
)


CACHE_SCHEMA_VERSION = 3


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

generate_tab, analyze_tab, model_tab, backtest_tab, research_tab = st.tabs(
    ["Generate", "Analyze Ticket", "Model Lab", "Backtesting", "Research Lab"]
)


@st.cache_data
def ranked_tickets(data, simulations, half_life, top_k, variant_name):
    return generate_ranked_tickets(
        data,
        simulations=simulations,
        half_life=half_life,
        top_k=top_k,
        score_weights=MODEL_VARIANTS.get(variant_name),
    )


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


@st.cache_data
def anti_crowd_tickets(count, simulations, random_seed, schema_version):
    return generate_anti_crowd_tickets(count=count, simulations=simulations, random_seed=random_seed)


with generate_tab:
    st.subheader("Generate")
    generation_mode = st.radio(
        "Generator",
        [
            "Best current model",
            "Anti-crowd",
            "Balanced mix",
            "Recent hot numbers",
            "Cold numbers",
            "Cluster hot numbers",
        ],
        horizontal=True,
    )
    generator_seed = st.number_input("Generator seed", min_value=1, max_value=9999, value=42, step=1)

    ticket_balls = None
    ticket_stars = None
    model_ticket = None
    source_rows = []

    if generation_mode == "Best current model":
        generator_half_life = st.slider(
            "Generator half-life", min_value=25, max_value=250, value=250, step=25, key="generate_half_life"
        )
        generator_simulations = st.slider(
            "Generator candidates", min_value=250, max_value=5000, value=1000, step=250, key="generate_simulations"
        )
        model_ticket = generate_ranked_tickets(
            df,
            simulations=generator_simulations,
            half_life=generator_half_life,
            top_k=1,
            random_seed=int(generator_seed),
            score_weights=MODEL_VARIANTS["No balance score"],
        )[0]
        ticket_balls, ticket_stars = model_ticket.balls, model_ticket.stars
        source_rows = [
            {"Signal": "Model variant", "Value": "No balance score"},
            {"Signal": "Model score", "Value": f"{model_ticket.score:.3f}"},
            {"Signal": "Hot", "Value": f"{model_ticket.hot_score:.3f}"},
            {"Signal": "Cold", "Value": f"{model_ticket.cold_score:.3f}"},
            {"Signal": "Spread", "Value": f"{model_ticket.spread_score:.3f}"},
            {"Signal": "Pairs", "Value": f"{model_ticket.pair_score:.3f}"},
        ]
    elif generation_mode == "Anti-crowd":
        behavior_simulations = st.slider(
            "Behavior candidates sampled", min_value=250, max_value=5000, value=2000, step=250, key="generate_behavior_simulations"
        )
        anti_crowd = anti_crowd_tickets(1, behavior_simulations, int(generator_seed), CACHE_SCHEMA_VERSION)[0]
        ticket_balls, ticket_stars = anti_crowd.balls, anti_crowd.stars
        source_rows = [
            {"Signal": "Crowding risk", "Value": f"{anti_crowd.crowding_risk_score:.1%}"},
            {"Signal": "Anti-popularity", "Value": f"{anti_crowd.anti_popularity_score:.1%}"},
            {"Signal": "Birthday bias", "Value": f"{anti_crowd.birthday_bias_score:.1%}"},
            {"Signal": "Pattern", "Value": f"{anti_crowd.playslip_pattern_score:.1%}"},
        ]
    else:
        top_n = st.slider("Candidate pool size", min_value=5, max_value=20, value=10, key="generate_pool")
        if generation_mode == "Cluster hot numbers":
            selected_cluster = st.selectbox("Choose a cluster", sorted(df_clustered["Cluster"].unique()))
            working_df = df_clustered[df_clustered["Cluster"] == selected_cluster]
            candidates = get_top_numbers(working_df, top_n)
        elif generation_mode == "Recent hot numbers":
            working_df = filter_recent_draws(df, recent_draw_count)
            candidates = get_top_numbers(working_df, top_n)
        elif generation_mode == "Cold numbers":
            candidates = get_cold_numbers(df, top_n)
        else:
            candidates = get_top_numbers(filter_recent_draws(df, recent_draw_count), top_n)

        generator_rng = random.Random(int(generator_seed))
        if generation_mode == "Balanced mix":
            ticket_balls, ticket_stars = generate_balanced_ticket(df, recent_draw_count, generator_rng)
        else:
            ticket_balls, ticket_stars = generate_ticket(candidates, generator_rng)
        top_balls, top_stars = candidates
        source_rows = [
            {"Signal": "Ball pool", "Value": str([number for number, _ in top_balls])},
            {"Signal": "Star pool", "Value": str([number for number, _ in top_stars])},
        ]

    if ticket_balls and ticket_stars:
        behavior = analyse_ticket_behavior(ticket_balls, ticket_stars)
        st.success(f"Ticket: Balls {ticket_balls} | Lucky Stars {ticket_stars}")
        col_model, col_crowd, col_anti = st.columns(3)
        col_model.metric("Model score", f"{model_ticket.score:.3f}" if model_ticket else "n/a")
        col_crowd.metric("Crowding risk", f"{behavior.crowding_risk_score:.1%}")
        col_anti.metric("Anti-popularity", f"{behavior.anti_popularity_score:.1%}")
        st.dataframe(source_rows, use_container_width=True, hide_index=True)


with analyze_tab:
    st.subheader("Analyze a ticket")
    input_balls = st.multiselect(
        "Balls", options=list(range(1, 51)), default=[4, 14, 17, 31, 41], max_selections=5, key="analyze_balls"
    )
    input_stars = st.multiselect(
        "Lucky Stars", options=list(range(1, 13)), default=[2, 8], max_selections=2, key="analyze_stars"
    )

    if len(input_balls) == 5 and len(input_stars) == 2:
        behavior = analyse_ticket_behavior(input_balls, input_stars)
        score_cols = st.columns(3)
        score_cols[0].metric("Crowding risk", f"{behavior.crowding_risk_score:.1%}")
        score_cols[1].metric("Anti-popularity", f"{behavior.anti_popularity_score:.1%}")
        score_cols[2].metric("Birthday bias", f"{behavior.birthday_bias_score:.1%}")

        behavior_rows = [
            {"Signal": "Lucky-number pull", "Score": behavior.lucky_number_score},
            {"Signal": "Round-number pull", "Score": behavior.round_number_score},
            {"Signal": "Consecutive run", "Score": behavior.consecutive_score},
            {"Signal": "Decade clustering", "Score": behavior.decade_cluster_score},
            {"Signal": "Playslip pattern", "Score": behavior.playslip_pattern_score},
            {"Signal": "Star popularity", "Score": behavior.star_popularity_score},
        ]
        behavior_display = pd.DataFrame(behavior_rows)
        behavior_display["Score"] = behavior_display["Score"].map(lambda value: f"{value:.1%}")
        st.dataframe(behavior_display, use_container_width=True, hide_index=True)
    else:
        st.warning("Choose exactly five balls and two Lucky Stars.")

    st.caption("Behavior scores estimate common selection patterns. They do not change draw probability.")


with model_tab:
    st.subheader("Ranked ticket model")
    model_variant = st.selectbox(
        "Model variant",
        ["Full model", "No balance score", "No cold score", "Only balance/spread"],
        index=1,
    )
    half_life = st.slider("Recency half-life", min_value=25, max_value=250, value=250, step=25, key="model_half_life")
    simulations = st.slider(
        "Monte Carlo candidates", min_value=250, max_value=5000, value=1000, step=250, key="model_simulations"
    )
    top_k = st.slider("Ranked tickets to show", min_value=3, max_value=10, value=5, key="model_top_k")

    tickets = ranked_tickets(df, simulations, half_life, top_k, model_variant)
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


with backtest_tab:
    st.subheader("Walk-forward backtest")
    test_draws = st.slider("Test draw count", min_value=50, max_value=500, value=200, step=50, key="backtest_draws")
    training_window = st.slider(
        "Minimum training draws", min_value=100, max_value=800, value=300, step=50, key="backtest_training"
    )
    backtest_simulations = st.slider(
        "Backtest candidates per draw", min_value=100, max_value=1000, value=300, step=100, key="backtest_simulations"
    )

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
        "expected_prize_value",
        "expected_net_value",
        "return_ratio",
        "roi",
        "total_prize_value",
    ]:
        summary[column] = summary[column].round(3)
    for column in ["expected_prize_value", "expected_net_value", "total_prize_value"]:
        summary[column] = summary[column].map(lambda value: f"£{value:,.2f}")
    for column in ["return_ratio", "roi"]:
        summary[column] = summary[column].map(lambda value: f"{value:.1%}")

    st.dataframe(summary, use_container_width=True, hide_index=True)

    with st.expander("Prize-tier value distribution"):
        tier_values = summarise_prize_tier_values(results).copy()
        for column in ["Hit rate", "Share of strategy value"]:
            tier_values[column] = tier_values[column].map(lambda value: f"{value:.1%}")
        for column in ["Estimated prize value", "Total prize value"]:
            tier_values[column] = tier_values[column].map(lambda value: f"£{value:,.2f}")
        st.dataframe(tier_values.drop(columns=["Prize tier rank"]), use_container_width=True, hide_index=True)

    with st.expander("Total-match distribution"):
        match_distribution = summarise_match_distribution(results).copy()
        for column in ["match_0_rate", "match_1_rate", "match_2_rate", "match_3_plus_rate", "total_match_std"]:
            match_distribution[column] = match_distribution[column].round(3)
        st.dataframe(match_distribution, use_container_width=True, hide_index=True)

    expected = theoretical_expected_matches()
    st.metric("Theoretical random expected matches", round(expected["total_matches"], 3))
    expected_return = theoretical_expected_return()
    col_gross, col_net, col_roi = st.columns(3)
    col_gross.metric("Theoretical prize EV", f"£{expected_return['expected_prize_value']:,.2f}")
    col_net.metric("Theoretical net EV", f"£{expected_return['expected_net_value']:,.2f}")
    col_roi.metric("Theoretical ROI", f"{expected_return['expected_roi']:.1%}")
    with st.expander("Theoretical prize-tier odds"):
        odds = theoretical_prize_probabilities().copy()
        odds["Probability"] = odds["Probability"].map(lambda value: f"{value:.10f}")
        odds["Odds 1 in"] = odds["Odds 1 in"].round(0).astype(int)
        for column in ["Estimated prize value", "Expected value contribution"]:
            odds[column] = odds[column].map(lambda value: f"£{value:,.4f}")
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
        "mean_expected_prize_value",
        "value_ci_low",
        "value_ci_high",
        "mean_expected_net_value",
        "mean_roi",
        "win_rate_vs_random",
        "avg_total_edge_vs_random",
        "avg_hit_edge_vs_random",
        "avg_value_edge_vs_random",
    ]:
        if column in repeated_summary.columns:
            repeated_summary[column] = repeated_summary[column].round(3)
    for column in ["mean_expected_prize_value", "value_ci_low", "value_ci_high", "mean_expected_net_value", "avg_value_edge_vs_random"]:
        if column in repeated_summary.columns:
            repeated_summary[column] = repeated_summary[column].map(lambda value: "" if pd.isna(value) else f"£{value:,.2f}")
    if "mean_roi" in repeated_summary.columns:
        repeated_summary["mean_roi"] = repeated_summary["mean_roi"].map(lambda value: f"{value:.1%}")

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
        "expected_prize_value",
        "expected_net_value",
        "return_ratio",
        "roi",
        "total_prize_value",
        "match_0_rate",
        "match_1_rate",
        "match_2_rate",
        "match_3_plus_rate",
        "total_match_std",
    ]:
        if column in ablation_display.columns:
            ablation_display[column] = ablation_display[column].round(3)
    for column in ["expected_prize_value", "expected_net_value", "total_prize_value"]:
        if column in ablation_display.columns:
            ablation_display[column] = ablation_display[column].map(lambda value: f"£{value:,.2f}")
    for column in ["return_ratio", "roi"]:
        if column in ablation_display.columns:
            ablation_display[column] = ablation_display[column].map(lambda value: f"{value:.1%}")
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
            "expected_prize_value",
            "expected_net_value",
            "return_ratio",
            "roi",
            "match_0_rate",
            "match_1_rate",
            "match_2_rate",
            "match_3_plus_rate",
            "total_match_std",
        ]:
            if column in display_sweep.columns:
                display_sweep[column] = display_sweep[column].round(3)
        for column in ["expected_prize_value", "expected_net_value"]:
            if column in display_sweep.columns:
                display_sweep[column] = display_sweep[column].map(lambda value: f"£{value:,.2f}")
        for column in ["return_ratio", "roi"]:
            if column in display_sweep.columns:
                display_sweep[column] = display_sweep[column].map(lambda value: f"{value:.1%}")

        st.dataframe(display_sweep, use_container_width=True, hide_index=True)
        chart_source = sweep[
            (sweep["training_window"] == sweep["training_window"].min())
            & (sweep["recent_draw_count"] == sweep["recent_draw_count"].min())
        ]
        hit_rate_chart = chart_source.pivot(index="half_life", columns="simulations", values="prize_hit_rate")
        value_chart = chart_source.pivot(index="half_life", columns="simulations", values="expected_prize_value")
        match_chart = chart_source.pivot(index="half_life", columns="simulations", values="avg_total_matches")
        st.line_chart(hit_rate_chart, use_container_width=True)
        st.line_chart(value_chart, use_container_width=True)
        st.line_chart(match_chart, use_container_width=True)
    else:
        st.info("Choose at least one value for each sweep dimension.")
