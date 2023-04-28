import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import os
import platform
import json
import sys
import time
import re
from tqdm import tqdm
import pandas as pd

CLIENT_LOG_PATTERN = re.compile(
    r'connection closed, recv=(-?\d+) sent=(-?\d+) lost=(-?\d+) rtt=(?:(?:(\d|.+)ms)|(?:(-1))) cwnd=(-?\d+), total_bytes=(-?\d+), complete_bytes=(-?\d+), good_bytes=(-?\d+), total_time=(-?\d+)')
CLIENT_STAT_INDEXES = ["c_recv", "c_sent", "c_lost",
                       "c_rtt(ms)", "c_cwnd", "c_total_bytes", "c_complete_bytes", "c_good_bytes", "c_total_time(us)", "qoe", "retry_times"]
CLIENT_BLOCKS_INDEXES = ["BlockID", "bct", "BlockSize", "Priority", "Deadline"]


def parse_client_log(logpath):
    '''
    Parse client.log and get two dicts of information.

    `client_blocks_dict` stores information in client.log about block's stream_id, bct, deadline and priority
    `client_stat_dict` stores statistics offered in client.log. Some important information is like goodbytes and total running time(total time)
    '''
    # collect client blocks information
    client_blocks_dict = {}
    for index in CLIENT_BLOCKS_INDEXES:
        client_blocks_dict[index] = []
    # collect client stats
    client_stat_dict = {}
    for index in CLIENT_STAT_INDEXES:
        client_stat_dict[index] = []

    with open(logpath) as client:
        client_lines = client.readlines()

        for line in client_lines[4:-1]:
            if len(line) > 1:
                client_line_list = line.split()
                if len(client_line_list) != len(CLIENT_BLOCKS_INDEXES):
                    print(
                        "A client block log line has error format in : %s. This happens sometime." % dir_path)
                    continue
                for i in range(len(client_line_list)):
                    client_blocks_dict[CLIENT_BLOCKS_INDEXES[i]].append(
                        client_line_list[i])

        # try to parse the last line of client log
        try:
            match = CLIENT_LOG_PATTERN.match(client_lines[-1])
            if match == None:
                raise ValueError(
                    "client re match returns None in : %s" % dir_path, client_lines[-1])

            client_stat_dict["c_recv"].append(float(match.group(1)))
            client_stat_dict["c_sent"].append(float(match.group(2)))
            client_stat_dict["c_lost"].append(float(match.group(3)))

            if match.group(4) is None:
                client_stat_dict["c_rtt(ms)"].append(float(-1))
            else:
                client_stat_dict["c_rtt(ms)"].append(float(match.group(4)))

            client_stat_dict["c_cwnd"].append(float(match.group(6)))
            client_stat_dict["c_total_bytes"].append(float(match.group(7)))
            client_stat_dict["c_complete_bytes"].append(float(match.group(8)))
            client_stat_dict["c_good_bytes"].append(float(9))
            client_stat_dict["c_total_time(us)"].append(float(match.group(10)))

            # invalid stat
            client_stat_dict["qoe"].append(-1)
            client_stat_dict["retry_times"].append(-1)

            return client_blocks_dict, client_stat_dict
        except:
            return None, None


def parse_result_old(result_file_name: str) -> pl.DataFrame:
    """
    # parse_result

    Parse a result file and return a polars DataFrame.

        Parameters:
            result_file_name (str): The name of the result file.

        Returns:
            polars.DataFrame: The parsed result.

    Format of the log file:
        - BlockID
        - bct
        - BlockSize
        - Priority
        - Deadline

    Format of the result file:
        CSV file with following columns:
        - block_id
        - bct
        - size
        - priority
        - deadline
        - duration
    """
    try:
        log = pl.read_csv(result_file_name)
        result = pl.DataFrame()
        result["block_id"] = log["BlockID"].apply(lambda x: (x >> 2) - 1)
        result["bct"] = log["bct"]
        result["size"] = log["BlockSize"]
        result["priority"] = log["Priority"]
        result["deadline"] = log["Deadline"]
        result["duration"] = log["bct"].apply(lambda x: -1)
        return result
    except Exception as e:
        print(e)
        return pl.DataFrame(
            None, ["block_id", "bct", "size",
                   "priority", "deadline", "duration"]
        )


def get_table_stats_old(finish_times, result_file_paths, trace_file_path="", labels=[]):
    print("stats of %s" % str(result_file_paths))
    while len(labels) < len(result_file_paths):
        labels.append("#" + str(len(labels)))
    result_throughput = []
    result_goodput = []
    result_avg_bct = []
    result_prio1_bct = []
    result_prio2_bct = []
    for idx, result_file_path in enumerate(result_file_paths):
        result = parse_result_old(result_file_path)
        in_time = result.filter(pl.col("bct") <= pl.col("deadline"))
        good_bytes = np.sum(in_time["size"].to_numpy())
        total_bytes = np.sum(result["size"].to_numpy())
        # finish_time = result["duration"][-1] # micro
        throughput = total_bytes * 8 / finish_times[idx]  # Mbps
        goodput = good_bytes * 8 / finish_times[idx]  # Mbps
        avg_bct = np.average(result["bct"].to_numpy())  # ms

        result_throughput.append(throughput)
        result_goodput.append(goodput)
        result_avg_bct.append(avg_bct)

        prio_result = result.partition_by("priority")
        for idx, prio_frame in enumerate(prio_result):
            avg_prio_bct = np.average(prio_frame["bct"].to_numpy())  # ms
            if prio_frame["priority"][0] == 1:
                result_prio1_bct.append(avg_prio_bct)
            elif prio_frame["priority"][0] == 2:
                result_prio2_bct.append(avg_prio_bct)
            else:
                print("priority %d is not expected" %
                      (prio_frame["priority"][0]))
    print("|\t| %s |" % (" | ".join(labels)))
    print("| Throughput (Mbps) | %s |" % (" | ".join(
        [x for x in map(lambda x: "%0.2f" % (x), result_throughput)])))
    print("| Goodput (Mbps) | %s |" %
          (" | ".join([x for x in map(lambda x: "%0.2f" % (x), result_goodput)])))
    print("| 平均块完成时间 (ms) | %s |" % (" | ".join(
        [x for x in map(lambda x: "%d" % (int(x)), result_avg_bct)])))
    # print(result_avg_bct)
    if result_avg_bct[1]-result_avg_bct[0] > 0:
        print("| DTP 平均块完成时间比TCP高百分",
              ((result_avg_bct[1]-result_avg_bct[0])/result_avg_bct[1])*100)
    print("| 高优先级块平均完成时间 (ms) | %s |" % (" | ".join(
        [x for x in map(lambda x: "%d" % (int(x)), result_prio1_bct)])))
    print("| 低优先级块平均完成时间 (ms) | %s |" % (" | ".join(
        [x for x in map(lambda x: "%d" % (int(x)), result_prio2_bct)])))


def get_finish_times(log_file_paths):
    times = []
    result_file_paths = []
    for file in log_file_paths:
        client_blocks_dict, client_stat_dict = parse_client_log(file)
        blocks = pd.DataFrame(client_blocks_dict)
        # stats = pd.DataFrame(client_stat_dict)
        result_file_name = file + ".csv"
        blocks.to_csv(result_file_name, index=False)
        result_file_paths.append(result_file_name)
        # stats.to_csv("dtp_stats.csv", index=False)
        times.append(int(client_stat_dict["c_total_time(us)"][0]))
    return times, result_file_paths


if __name__ == "__main__":
    log_files = ["../data/dtp_client.log", "../data/tcp_client.log"]
    finish_times, result_file_paths = get_finish_times(log_files)
    get_table_stats_old(finish_times, result_file_paths,
                        "../data/aitrans_block.txt", ["DTP", "TCP"])
