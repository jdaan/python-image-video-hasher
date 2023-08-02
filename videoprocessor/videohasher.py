import os
import sys

from PIL import Image

import ffmpeg
import uuid
import imagehash
import database
import distance
import numpy as np


def import_videos(video, message_id):
    """
    Import video's from the video directory
    :param video:
    :param message_id:
    :return:
    """
    hashes = generate_hashes(video)

    database.add_video(os.path.basename(video), hashes, message_id)


def process_video(video, message_id):
    """
    Process a given video and add it to the db (if it isn't a repost)
    :param video:
    :param message_id:
    :return:
    """
    hashes = generate_hashes(video)

    sim_vids = check_for_similar(hashes)

    if len(sim_vids) > 0:
        return sim_vids
    else:
        database.add_video(os.path.basename(video), hashes, message_id)
        return False


def check_video(video):
    """
    Only check if the given video is a reee
    :param video:
    :return:
    """
    hashes = generate_hashes(video)
    sim_vids = check_for_similar(hashes)

    if len(sim_vids) > 0:
        return sim_vids
    else:
        return False


def check_for_similar(hashes):
    """
    Check if the given hashes can be mapped to a video in the DB
    :param hashes:
    :return:
    """
    all_videos = database.get_all_videos()

    sim_vids = []

    for vid in all_videos:
        vid_hashes = eval(vid[1])

        if len(vid_hashes) >= 19 and len(hashes) >= 19:
            total_sim = 0
            for i in range(len(hashes)):
                dist = distance.hamming(str(vid_hashes[i]), str(hashes[i]))
                dist_perc = round((100 - ((64 / 100) * dist)), 2)

                if dist_perc > 70:
                    total_sim = total_sim + 1

            total_sim_perc = round((100 / 19) * total_sim)

            if total_sim_perc > 35:
                vid = vid + (total_sim_perc,)
                sim_vids.append(vid)

    return sim_vids


def generate_hashes(video):
    """
    Generate 19/20 thumbnails from the given video and hash each thumb
    then return the thumbs as an array
    :param video:
    :return:
    """
    thumbnails = generate_thumbnails_from_file(video)

    hashes = []

    for h in thumbnails[0]:
        hashes.append(str(imagehash.dhash(Image.open(h), 16)))
        os.remove(h)

    return hashes


def generate_thumbnails_from_file(video_file: str, total_thumbs: int = 20) -> list:
    """
    Generate thumbnails from the given file using ffmpeg
    :param video_file:
    :param total_thumbs:
    :return:
    """
    result = {
        'duration': None,
        'thumbs': []
    }
    try:
        probe = ffmpeg.probe(video_file)
    except Exception as e:
        print('Failed to probe video: %s', video_file)
        raise

    duration = float(probe['format']['duration'])
    interval = float(probe['format']['duration']) / total_thumbs
    count = 1
    seek = interval

    output_dir = os.path.split(video_file)[0] + '/temp/'
    random_id = uuid.uuid1()

    thumb_files = []

    while count <= total_thumbs:
        thumb_file = os.path.join(output_dir, '{}-{}.png'.format(str(random_id), str(count)))

        try:
            (
                ffmpeg.input(video_file, ss=seek)
                      .filter('scale', 720, -1)
                      .output(thumb_file, vframes=1)
                      .overwrite_output()
                      .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            print(e.stderr.decode(), file=sys.stderr)

        if os.path.exists(thumb_file):
            thumb_files.append(thumb_file)

        seek += interval
        count += 1

    return [thumb_files, duration]
