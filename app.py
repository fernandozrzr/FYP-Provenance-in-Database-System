from flask import Flask, request, render_template
from collections import Counter
import subprocess
import os
import re
import csv
from io import StringIO

app = Flask(__name__)
os.makedirs("static", exist_ok=True)


# Normalize SQL queries
def normalize_sql(sql: str) -> str:
    return " ".join(line.strip() for line in sql.strip().splitlines())


# Robust parsers
def parse_psql_ascii_table(output: str):

    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    columns = []
    data_rows = []

    # Find header line (the line before the separator ---+---+---)
    header_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*-+\s*(\+-+\s*)*$", line):
            header_idx = i - 1
            break

    if header_idx is not None and 0 <= header_idx < len(lines):
        columns = [c.strip() for c in lines[header_idx].split("|")]
        # Data lines are after the separator
        for l in lines[header_idx + 2 :]:
            if "|" in l and not re.match(r"^\s*-+\s*(\+-+\s*)*$", l):
                row = [cell.strip() for cell in l.split("|")]
                if any(cell != "" for cell in row):
                    data_rows.append(row)
    else:
        # fallback: just split by pipes, first row = header
        data_rows_candidate = [r for r in lines if "|" in r]
        if data_rows_candidate:
            columns = [c.strip() for c in data_rows_candidate[0].split("|")]
            for r in data_rows_candidate[1:]:
                row = [c.strip() for c in r.split("|")]
                data_rows.append(row)

    if data_rows and all(len(r) == len(columns) and r[-1] == "" for r in data_rows):
        columns = columns[:-1]
        data_rows = [r[:-1] for r in data_rows]

    return columns, data_rows


def parse_csv_like_output(output: str):

    f = StringIO(output)
    reader = csv.reader(f, delimiter=",")
    all_rows = list(reader)
    if not all_rows:
        return [], []
    columns = all_rows[0]
    rows = all_rows[1:] if len(all_rows) > 1 else []
    return columns, rows


@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    query = ""
    mode = "default"
    engine = "gprom"
    timestamp = ""
    main_select = ""
    subquery = ""
    baserelation = ""
    has_attrs = ""
    group_by_attrs = ""
    use_attrs = ""
    semirings_table = ""
    semirings_subquery = ""
    view_uuid = ""
    view_table = ""
    wp_subquery = ""
    prob_method = ""
    prob_subquery = ""
    full_query = ""
    action = ""

    columns = []
    result_rows = []
    chart_labels = []
    chart_values = []

    if request.method == "POST":
        # --- Get all form fields ---
        query = normalize_sql(request.form.get("query", ""))
        mode = request.form.get("mode", "default")
        engine = request.form.get("engine", "gprom")
        timestamp = request.form.get("timestamp", "").strip()
        main_select = normalize_sql(request.form.get("main_select", ""))
        subquery = normalize_sql(request.form.get("subquery", ""))
        baserelation = request.form.get("baserelation", "").strip()
        has_attrs = request.form.get("has_attrs", "").strip()
        group_by_attrs = request.form.get("group_by_attrs", "").strip()
        use_attrs = request.form.get("use_attrs", "").strip()
        semirings_table = request.form.get("semirings_table", "").strip()
        semirings_subquery = normalize_sql(request.form.get("semirings_subquery", ""))
        view_uuid = request.form.get("view_uuid", "").strip()
        view_table = request.form.get("view_table", "").strip()
        action = request.form.get("action", "Run Query")
        wp_subquery = normalize_sql(request.form.get("wp_subquery", ""))
        prob_method = request.form.get("prob_method", "").strip()
        prob_subquery = normalize_sql(request.form.get("prob_subquery", ""))

        try:
            # --- GProM Engine ---
            if engine == "gprom":
                if mode == "provenance":
                    full_query = f"PROVENANCE OF ({query});"
                elif mode == "timestamp" and timestamp:
                    full_query = (
                        f"PROVENANCE AS OF TIMESTAMP '{timestamp}' OF ({query});"
                    )
                elif (
                    mode == "baserelation" and main_select and subquery and baserelation
                ):
                    full_query = f"PROVENANCE OF ({main_select} ( {subquery} ) BASERELATION AS {baserelation});"
                elif mode == "has_provenance" and has_attrs:
                    upper_query = query.upper()
                    if "FROM" in upper_query:
                        from_idx = upper_query.index("FROM") + len("FROM")
                        before_from = query[:from_idx]
                        after_from = query[from_idx:].strip()
                        full_query = f"PROVENANCE OF ({before_from} {after_from} HAS PROVENANCE ({has_attrs})"
                    else:
                        full_query = (
                            f"PROVENANCE OF ({query} HAS PROVENANCE ({has_attrs})"
                        )
                    if group_by_attrs:
                        full_query += f" GROUP BY {group_by_attrs}"
                    full_query += ");"
                elif mode == "use_provenance" and use_attrs:
                    upper_query = query.upper()
                    if "FROM" in upper_query:
                        from_idx = upper_query.index("FROM") + len("FROM")
                        before_from = query[:from_idx]
                        after_from = query[from_idx:].strip()
                        full_query = f"PROVENANCE OF ({before_from} {after_from} USE PROVENANCE ({use_attrs})"
                    else:
                        full_query = (
                            f"PROVENANCE OF ({query} USE PROVENANCE ({use_attrs})"
                        )
                    if group_by_attrs:
                        full_query += f" GROUP BY {group_by_attrs}"
                    full_query += ");"
                elif mode == "reenact":
                    full_query = f"REENACT ({query});"
                elif mode == "reenact_provenance":
                    full_query = f"REENACT WITH PROVENANCE ({query});"
                elif mode == "reenact_annotations":
                    full_query = f"REENACT WITH PROVENANCE ONLY UPDATED SHOW INTERMEDIATE STATEMENT ANNOTATIONS ({query});"
                else:
                    full_query = query.rstrip(";") + ";"

                # --- Execute GProM ---
                if action == "Run Query":
                    gprom_cmd = [
                        "/home/user/gprom/src/command_line/gprom",
                        "-db",
                        "gprom_db",
                        "-backend",
                        "postgres",
                        "-host",
                        "localhost",
                        "-port",
                        "5432",
                        "-user",
                        "postgres",
                    ]
                    process = subprocess.Popen(
                        gprom_cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    stdout, stderr = process.communicate(input=full_query + "\n\\q\n")
                    result = stdout if stdout else stderr
                elif action == "Generate Image":
                    gprom_cmd = [
                        "/home/user/gprom/src/command_line/gprom",
                        "-db",
                        "gprom_db",
                        "-backend",
                        "postgres",
                        "-host",
                        "localhost",
                        "-port",
                        "5432",
                        "-user",
                        "postgres",
                        "-show_graphviz",
                        "-graphviz_details",
                        "-query",
                        full_query,
                    ]
                    with open("provenance_output.txt", "w") as f:
                        subprocess.run(
                            gprom_cmd,
                            stdout=f,
                            stderr=subprocess.STDOUT,
                            text=True,
                            check=True,
                        )

                    # Extract graph from output
                    found = False
                    depth = 0
                    with open("provenance_output.txt") as infile, open(
                        "output.dot", "w"
                    ) as outfile:
                        for line in infile:
                            if not found and "GRAPHVIZ: AFTER OPTIMIZATIONS" in line:
                                found = True
                                continue
                            if found:
                                if "digraph G {" in line:
                                    depth = 1
                                    outfile.write(line)
                                    continue
                                if depth > 0:
                                    outfile.write(line)
                                    depth += line.count("{") - line.count("}")
                                    if depth == 0:
                                        break
                    subprocess.run(
                        ["dot", "-Tpng", "output.dot", "-o", "static/output.png"],
                        check=True,
                    )
                    result = "Graph generated below:"

            # --- ProvSQL Engine ---
            elif engine == "provsql":
                if mode == "default":
                    full_query = query.rstrip(";") + ";"
                elif mode == "add_provenance":
                    full_query = f"SELECT add_provenance({query});"
                elif mode == "create_provenance_mapping":
                    full_query = f"SELECT create_provenance_mapping({query});"
                elif mode == "semirings":
                    if semirings_table and semirings_subquery:
                        full_query = (
                            f"SELECT *, SR_FORMULA(PROVENANCE(), {semirings_table}) "
                            f"FROM ({semirings_subquery}) t;"
                        )
                        if action == "Generate Image":
                            # Step 1: Write the SQL to a file
                            sql_commands = f"""
                            SET search_path TO provsql_test, provsql;
                            \\copy ({full_query.rstrip(';')}) TO '/tmp/prov_output.csv' CSV HEADER ENCODING 'UTF8';
                            """
                            with open("temp_export.sql", "w", encoding="utf-8") as f:
                                f.write(sql_commands)

                            # Step 2: Copy the SQL file into the container
                            subprocess.run(
                                [
                                    "docker",
                                    "cp",
                                    "temp_export.sql",
                                    "provsql-demo:/tmp/temp_export.sql",
                                ],
                                check=True,
                            )

                            # Step 3: Execute it inside the container
                            subprocess.run(
                                [
                                    "docker",
                                    "exec",
                                    "-i",
                                    "provsql-demo",
                                    "psql",
                                    "-U",
                                    "test",
                                    "-d",
                                    "test",
                                    "-f",
                                    "/tmp/temp_export.sql",
                                ],
                                check=True,
                            )

                            # Step 4: Copy the exported CSV back out
                            subprocess.run(
                                [
                                    "docker",
                                    "cp",
                                    "provsql-demo:/tmp/prov_output.csv",
                                    "./static/prov_output.csv",
                                ],
                                check=True,
                            )

                            # Step 5: Clean up
                            os.remove("temp_export.sql")

                            # Step 6: Generate PNG
                            subprocess.run(
                                ["venv/bin/python3", "prov_graph.py"], check=True
                            )

                            result = (
                                "Graph generated as prov_graph.png in static folder."
                            )
                        elif action == "View Circuit":

                            if not view_uuid and not view_table:
                                return render_template(
                                    "index.html",
                                    full_query="-- Missing UUID or table for view_circuit",
                                    engine=engine,
                                    mode=mode,
                                )
                           
                            first_query = full_query
                            full_query = f"SELECT VIEW_CIRCUIT({view_uuid}, {view_table});"
                            both_query = first_query + " " + full_query

                            # Execute query inside Docker and capture output as text
                            docker_cmd = [
                                "docker",
                                "exec",
                                "-i",
                                "provsql-demo",
                                "psql",
                                "-U",
                                "test",
                                "-d",
                                "test",
                                "-c",
                                both_query,
                            ]
                            result = subprocess.run(docker_cmd, capture_output=True, text=True)

                            # Capture the raw ASCII circuit output
                            raw_output = result.stdout or result.stderr

                            # Mark result as raw text
                            return render_template(
                                "index.html",
                                full_query=full_query,
                                result_type="raw",
                                raw_output=raw_output,
                                engine=engine,
                                mode=mode,
                                view_uuid=view_uuid,
                                view_table=view_table,
                                semirings_table=semirings_table,
                                semirings_subquery=semirings_subquery,
                                action=action,
                            )
                    else:
                        full_query = "-- Missing table or subquery for semirings"

                elif mode == "where_provenance":
                    if wp_subquery:
                        full_query = f"SELECT *, where_provenance(provenance()) FROM ({wp_subquery}) t;"
                    else:
                        full_query = "-- Missing subquery for WHERE_PROVENANCE"
                elif mode == "probability":
                    if prob_method and prob_subquery:
                        full_query = (
                            f"SELECT *, probability_evaluate(provenance(), {prob_method}) "
                            f"FROM ({prob_subquery}) t;"
                        )
                    else:
                        full_query = "-- Missing method or subquery for PROBABILITY"

                # Execute via Docker
                docker_cmd = [
                    "docker",
                    "exec",
                    "-i",
                    "provsql-demo",
                    "psql",
                    "-U",
                    "test",
                    "test",
                    "-c",
                    full_query,
                ]
                process = subprocess.Popen(
                    docker_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                stdout, stderr = process.communicate()
                result = stdout if stdout else stderr

        except Exception as e:
            result = f"[ERROR] {str(e)}\n\n---\nQuery attempted:\n{full_query if engine=='provsql' else query}"

        # --- Parse results robustly ---
        # --- Parse results robustly ---
        if any(
            x in result.strip().lower() for x in ["error", "fatal", "does not exist"]
        ):
            columns = []
            result_rows = []
        else:
            # Parse normally
            columns, result_rows = parse_psql_ascii_table(result)
            if not columns and not result_rows:
                columns, result_rows = parse_csv_like_output(result)

        # Chart data
        if result_rows:
            counts = Counter(r[0] for r in result_rows)
            chart_labels = list(counts.keys())
            chart_values = list(counts.values())

    return render_template(
        "index.html",
        columns=columns,
        result=result_rows,
        raw_output=result,
        result_type="table" if columns and result_rows else "raw",
        chart_labels=chart_labels,
        chart_values=chart_values,
        query=query,
        mode=mode,
        engine=engine,
        timestamp=timestamp,
        main_select=main_select,
        subquery=subquery,
        baserelation=baserelation,
        has_attrs=has_attrs,
        group_by_attrs=group_by_attrs,
        use_attrs=use_attrs,
        semirings_table=semirings_table,
        semirings_subquery=semirings_subquery,
        view_uuid=view_uuid,
        view_table=view_table,
        wp_subquery=wp_subquery,
        prob_method=prob_method,
        prob_subquery=prob_subquery,
        full_query=full_query,
        action=action,
    )


if __name__ == "__main__":
    app.run(debug=True)