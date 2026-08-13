from flask import Flask, render_template, request

app = Flask(__name__)

MEMBERS = {
    "12345": {
        "name": "Alex Morgan",
        "checking": "1,240.52",
        "savings": "4,231.44",
    },
    "67890": {
        "name": "Jordan Lee",
        "checking": "2,901.18",
        "savings": "823.19",
    },
    "55555": {
        "name": "Taylor Smith",
        "checking": "3,412.00",
        "savings": "1,105.75",
    },
}

TRANSIENT_FAILURES = {
    "55555": 0,
}


@app.route("/")
def home():
    return render_template("search.html")


@app.route("/member", methods=["POST"])
def member():
    member_id = request.form.get(
        "member_id",
        "",
    ).strip()

    if not member_id:
        return render_template(
            "search.html",
            error="Member ID is required.",
        )

    # Known authorization/runtime outcome.
    if member_id == "77777":
        return render_template(
            "search.html",
            error="Permission denied.",
            member_id=member_id,
        )

    # Simulated transient application failure.
    # The first attempt fails and a replay retry succeeds.
    if member_id == "55555":
        failure_count = TRANSIENT_FAILURES[
            member_id
        ]

        if failure_count == 0:
            TRANSIENT_FAILURES[
                member_id
            ] += 1

            return render_template(
                "search.html",
                error=(
                    "Temporary service error. "
                    "Please try again."
                ),
                member_id=member_id,
            )

    member_data = MEMBERS.get(
        member_id
    )

    if member_data is None:
        return render_template(
            "search.html",
            error="Member not found.",
            member_id=member_id,
        )

    return render_template(
        "member.html",
        member_id=member_id,
        member=member_data,
    )


if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000,
    )