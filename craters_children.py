"""
Find craters that lie within other craters.
"""
import numpy as np
import pandas as pd
import time
import json

from collections import defaultdict

# https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html
MOON_MEAN_RADIUS = 1737.4  # km


def correct_lon_column(df, lon_name):
    """
    Add 360 to all negative longitude values in dataframe.

    Has the side effect of modifying the passed in dataframe.

    df: Pandas dataframe
    name: Name of column in the dataframe
    """

    def bool_to_deg(x):
        if x:
            return 360
        return 0

    neg_lon = df[lon_name] < 0
    lon_correct_factor = [bool_to_deg(i) for i in neg_lon]
    df[lon_name] = df[lon_name] + lon_correct_factor


def great_cirlce_distance(a_lon, a_lat, b_lon, b_lat, radius=MOON_MEAN_RADIUS):
    """
    Calculate the great circle distance between two points.

    Assumes lon/lat is passed in degrees.
    """
    a_lon = np.deg2rad(a_lon)
    a_lat = np.deg2rad(a_lat)
    b_lon = np.deg2rad(b_lon)
    b_lat = np.deg2rad(b_lat)

    angle = np.arccos(
        np.sin(a_lat) * np.sin(b_lat)
        + np.cos(a_lat) * np.cos(b_lat) * np.cos(a_lon - b_lon)
    )
    return angle * radius


def crater_in_crater(c_lon, c_lat, p_lon, p_lat, p_diam):
    """
    Check if child crater c lies within parent crater p.
    """
    dist = great_cirlce_distance(c_lon, c_lat, p_lon, p_lat)
    return dist < p_diam / 2  # Use radius not diameter...


def crater_in_ncraters(c_lon, c_lat, p_df):
    """
    Find if child crater c lies within one of many parent craters.

    p_df has the colums: ["id", "lon", "lat", "diam"]

    Returns: ID of parent crater child crater lies within or None.
    """
    for p_crater in p_df.itertuples():
        if crater_in_crater(c_lon, c_lat, p_crater.lon, p_crater.lat, p_crater.diam):
            return p_crater.id
    return None


def ncraters_in_ncraters(c_df, p_df, progress=False):
    """
    Check if craters in child_df are in parent_df.

    Both input dataframes have the columns: ["id", "lon", "lat", "diam"]

    Has the side effect of adding a new column to parent_df called
    "children_ids", the set of IDs of child craters.
    """
    overlaps = defaultdict(set)

    c_ind = 0
    t_start = time.perf_counter()

    for c_crater in c_df.itertuples():
        parent_id = crater_in_ncraters(c_crater.lon, c_crater.lat, p_df)
        if parent_id:
            # return(parent_id, c_crater.id)
            overlaps[parent_id].add(c_crater.id)

        if progress and c_ind % 1000 == 1:
            percent = c_ind / len(c_df) * 100
            t_elapsed = time.perf_counter() - t_start
            rate = t_elapsed / percent
            t_est = (100 - percent) * rate
            print(
                f"{c_ind}/{len(c_df)}, {percent:.1f}, elapsed: {t_elapsed:.0f}, eta: {t_est:.0f}"
            )
        c_ind += 1

    return overlaps


def build_processed_craters():
    """
    Load and process Yang and Robbins datasets.

    Returns: Two dataframes, each with "id", "lon", "lat", and "diam" fields.
    """
    robbins_craters = pd.read_csv("./lunar_crater_database_robbins_2018.csv")
    robbins_lt_10 = robbins_craters["DIAM_CIRC_IMG"] < 10
    robbins_craters = robbins_craters[robbins_lt_10]
    child_craters = pd.DataFrame()
    child_craters["id"] = robbins_craters["CRATER_ID"]
    child_craters["lon"] = robbins_craters["LON_CIRC_IMG"]
    child_craters["lat"] = robbins_craters["LAT_CIRC_IMG"]
    child_craters["diam"] = robbins_craters["DIAM_CIRC_IMG"]

    yang_aged_craters = pd.read_csv("./yang_aged_database.csv")
    parent_craters = pd.DataFrame()
    parent_craters["id"] = yang_aged_craters["ID"]
    parent_craters["lon"] = yang_aged_craters["Lon"]
    parent_craters["lat"] = yang_aged_craters["Lat"]
    parent_craters["diam"] = yang_aged_craters["Diam_km"]
    parent_craters["age"] = yang_aged_craters["Age"]

    return parent_craters, child_craters


def correct_craters_in_craters():
    """
    Correct a craters in craters dict.

    Written to correct the incorrect data that used a diameter in place of a
    radius.
    """
    parent_craters, child_craters = build_processed_craters()

    with open("./robbins_in_yang.json", "r") as file:
        data = json.loads(file.read())

    def list_to_dataframe(p_id, c_list):
        crater_rows = child_craters["id"].map(lambda x: x in c_list)
        return child_craters[crater_rows]

    def craters_in_parent(parent_id, c_list):
        child_df = list_to_dataframe(parent_id, c_list)

        parent_row = parent_craters[parent_craters["id"] == int(parent_id)]
        parent_radius = float(parent_row["diam"] / 2)
        parent_lon = float(parent_row["lon"])
        parent_lat = float(parent_row["lat"])
        # Check that the distance between center of the parent and center of
        # each child is actually within the radius of the parent
        correct_rows = child_df.apply(
            lambda x: great_cirlce_distance(x["lon"], x["lat"], parent_lon, parent_lat)
            <= parent_radius,
            axis=1,
        )
        return list(child_df["id"][correct_rows])

    new_data = {p_id: craters_in_parent(p_id, c_list) for p_id, c_list in data.items()}
    new_data = {p_id: c_list for p_id, c_list in new_data.items() if len(c_list) > 0}
    with open("./new_data.json", "w") as f_out:
        f_out.write(json.dumps(new_data, indent=4))


def main():
    parent_craters, child_craters = build_processed_craters()

    results = ncraters_in_ncraters(child_craters, parent_craters, progress=True)

    robbins_in_yang = pd.DataFrame()
    yang_ids, robbins_ids = zip(*results.items())
    robbins_in_yang["yang_id"] = yang_ids
    robbins_in_yang["robbins_ids"] = robbins_ids

    with open("robbins_in_yang.csv", "w") as file:
        file.write(robbins_in_yang.to_csv(index=False))

    robbins_in_yang_no_set = {k: list(v) for k, v in robbins_in_yang.items()}
    with open("robbins_in_yang.json") as file:
        file.write(json.dumps(robbins_in_yang_no_set, indent=4))


if __name__ == "__main__":
    main()
