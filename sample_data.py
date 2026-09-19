def load_sample_data():

    import os

    if os.environ.get(
        "DEMO_MODE",
        ""
    ).lower() != "true":
        return

    # Keep the rest of your existing
    # sample-data generation code below.