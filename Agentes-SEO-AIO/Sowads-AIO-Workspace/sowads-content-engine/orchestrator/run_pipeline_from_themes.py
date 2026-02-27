#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import run_pipeline as rp


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pipeline using a fixed themes CSV (without agent01 generation)")
    parser.add_argument("--base", default=str(Path(__file__).resolve().parents[1]), help="Project root")
    parser.add_argument("--config", default="orchestrator/config.example.json", help="Config JSON path")
    parser.add_argument("--themes-file", required=True, help="CSV de temas fixos")
    args = parser.parse_args()

    base = Path(args.base).resolve()
    rp.load_env_file(base / ".env")
    rp.load_env_file(base.parent / ".env")

    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = base / cfg_path
    cfg = rp.load_config(cfg_path)

    pipe = rp.Pipeline(base, cfg)
    themes_path = Path(args.themes_file)
    if not themes_path.is_absolute():
        themes_path = (base / themes_path).resolve()
    themes = pipe._load_themes_from_csv(themes_path)

    pipe.log("pipeline", "start", metrics={"test_mode": pipe.test_mode, "mode": "from_themes_csv", "themes_count": len(themes)})

    article_state = pipe.agent02_generate_articles(themes)
    iteration = 1
    rp.write_csv(base / "outputs/articles" / f"{pipe.batch_id}_articles_v{iteration}.csv", list(article_state.values()), rp.ARTICLE_COLUMNS)
    rp.write_csv(pipe.batch_dir / f"articles_v{iteration}.csv", list(article_state.values()), rp.ARTICLE_COLUMNS)

    audit = pipe.agent03_audit(article_state)
    similarity = pipe.agent04_similarity(article_state)

    for _ in range(pipe.max_rewrites):
        audit_map = {x["id"]: x for x in audit["items"]}
        sim_map = {x["id"]: x for x in similarity["items"]}

        rewrite_map = {}
        for item_id in article_state.keys():
            if audit_map[item_id]["flags"]["flag_rewrite"]:
                rewrite_map[item_id] = audit_map[item_id]["rewrite_guidance"]
            elif sim_map[item_id]["flag_similarity"]:
                rewrite_map[item_id] = sim_map[item_id]["rewrite_guidance"]

        if not rewrite_map:
            break

        article_state = pipe.agent02_generate_articles(themes, current=article_state, rewrite_map=rewrite_map)
        iteration += 1
        rp.write_csv(base / "outputs/articles" / f"{pipe.batch_id}_articles_v{iteration}.csv", list(article_state.values()), rp.ARTICLE_COLUMNS)
        rp.write_csv(pipe.batch_dir / f"articles_v{iteration}.csv", list(article_state.values()), rp.ARTICLE_COLUMNS)
        audit = pipe.agent03_audit(article_state)
        similarity = pipe.agent04_similarity(article_state)

    audit_map = {x["id"]: x for x in audit["items"]}
    sim_map = {x["id"]: x for x in similarity["items"]}

    approved = {}
    for item_id, a in article_state.items():
        if audit_map[item_id]["seo_geo_score"] >= pipe.threshold and not audit_map[item_id]["flags"]["flag_rewrite"] and sim_map[item_id]["similarity_score"] <= 60:
            a["status"] = "APPROVED"
            approved[item_id] = a
        else:
            a["status"] = "REJECTED"

    rp.write_csv(base / "outputs/articles" / f"{pipe.batch_id}_articles.csv", list(article_state.values()), rp.ARTICLE_COLUMNS)
    pipe.agent05_image_prompts(approved)
    publish_results = pipe.agent06_publish(approved, audit_map, sim_map)
    pipe.update_history(approved, audit_map, sim_map)

    summary = {
        "batch_id": pipe.batch_id,
        "mode": "from_themes_csv",
        "themes_file": str(themes_path),
        "items_total": len(article_state),
        "approved": len(approved),
        "rejected": len(article_state) - len(approved),
        "iterations": iteration,
        "test_mode": pipe.test_mode,
        "publish_results": publish_results,
    }
    rp.write_json(pipe.batch_dir / "summary.json", summary)
    pipe.log("pipeline", "success", metrics=summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
