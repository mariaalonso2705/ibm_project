"""
 © Copyright IBM Corporation 2020.
Licensed under the BSD-3-Clause License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    https://opensource.org/licenses/BSD-3-Clause
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import cv2
import numpy as np
import json
import sys

# Constants
# Locations of the visible light and infrared panels in the full frame provided by the Stryker Pinpoint system
VIS = (slice(360), slice(480))
INFRA = (slice(360, 720), VIS[1])


def stryker(frame):
    # A function to extract the NIR frame and the visible light frame from the full video frame if the video is generated by the Stryker system
    return frame[VIS], frame[INFRA]


def box_to_slice(box):
    # converting a bounding box in [left, top, width, height] for to a slice which can be used to index frames
    return (slice(int(box[1]), int(box[1]+box[3])), slice(int(box[0]), int(box[0]+box[2])))


class tracker:
    # A tracker class wrapping the OpenCV MultiTracker API
    def __init__(self, rois, init_vis, init_infra=None, agg_func=np.median, spread_func=None):
        """
        rois : a list of lists. Every inner list is of the form [left, top, width, height] and denotes one roi
        init_vis : the first frame in visible light. NOTE: has to be grey scale for this tracker, so shape is (h,w)
        agg_func : optional. The function to aggregate intensities across one roi.
        spread_func : optional. This function should quantify the spread of the intensities across one roi. As an example, one could use spread_func=np.std
        """
        self.tracker = cv2.MultiTracker_create()
        for roi in rois:
            self.tracker.add(cv2.TrackerMedianFlow_create(),
                             init_vis, tuple(roi))
        self.agg_func = agg_func
        self.spread_func = spread_func

    def update(self, vis, infra):
        """
        vis : the frame in visible light. NOTE: the tracker works on grey scale only, so this is an array of shape (h,w)
        infra : the same frame in the infrared light. This can be an array of shape (h,w) or (h,w,c).
        returns
        rois : a list of the updated roi positions. Each element is a list [left, top, width, height]
        agg_intensities : a list of the average intensities of each roi as computed by tracker.agg_func
        spread_intensities : if tracker.spread_func is set (i.e. is not None), then the third output is a list of the same length as agg_intensities, containing the result of tracker.spread_func evaluted on each roi
        """
        succ, rois = self.tracker.update(vis)
        if not succ:
            print('[Warning]: at least one ROI was not detected')
        agg_intensities = []
        if self.spread_func is None:
            for roi in rois:
                agg_intensities.append(
                    self.agg_func(
                        infra[box_to_slice(roi)]
                    )
                )
            return rois, agg_intensities
        else:
            spread_intensities = []
            for roi in rois:
                agg_intensities.append(
                    self.agg_func(
                        infra[box_to_slice(roi)]
                    )
                )
                spread_intensities.append(
                    self.spread_func(
                        infra[box_to_slice(roi)]
                    )
                )
            return rois, agg_intensities, spread_intensities


'''
This function adds the data of frame,rois,agg_intensities into a Dict,which
is then later used to convert to a JSON file
'''


def convert_to_dict(rois, agg_intensities, spread_intensities):
    # Creates a dictionary with associated keys
    JSONDictionary = {'frame_number': {
        'roi': {'intensity', 'spread_intensity'}}}

    for i, roi_value in enumerate(rois):  # iterates through rois list
        # iterates through agg_intensities list
        for i, intensity_value in enumerate(agg_intensities):
            for i, spread_value in enumerate(spread_intensities):
                # appends the intensity values into the dictionary
                JSONDictionary[f'roi{i}'] = list(roi_value)
                try:
                    if np.isnan(intensity_value) or np.isnan(spread_value):
                        JSONDictionary[f'intensity{i}'] = -1
                        JSONDictionary[f'spread_intensity{i}'] = -1
                    else:
                        JSONDictionary[f'intensity{i}'] = intensity_value
                        JSONDictionary[f'spread_intensity{i}'] = spread_value
                except Exception as identifier:
                    print(identifier)

    return JSONDictionary


def convert_to_JSON_file(JSONDictionary):
    file_name = "Output.json"
    with open(file_name, "a") as f:
        JSONDictionary = json.dumps(JSONDictionary)
        f.write("%s,\n" % (JSONDictionary))
        f.close()
    return f


if __name__ == '__main__':

    def plot_roi(roi, frame):
        # very simple function plotting `roi` onto `frame`
        cv2.rectangle(frame, (int(roi[0]), int(roi[1])), (int(
            roi[0]+roi[2]), int(roi[1]+roi[3])), (0, 250, 0))

    open('Output.json', 'w').close()
    vidfile = input('Path to video:')
    # vidfile = "M_03292018202006_00000000U2940605_1_001-1.MP4"
    offset_ms = 70*1000
    frames_to_process = 500
    # Open the video file and fast forward to the offset
    cap = cv2.VideoCapture(vidfile)
    cap.set(cv2.CAP_PROP_POS_MSEC, offset_ms)
    # Read the first frame
    ret, frame0 = cap.read()
    # Extract the panels with visible light and infrared light images
    vis, infra = stryker(frame0)
    # two ROIs
    rois0 = [[10, 100, 30, 50], [100, 100, 50, 30]]
    #  tracker
    vanilla = tracker(rois0, init_vis=vis, spread_func=np.std)
    #  display the ROIs
    for roi in rois0:
        plot_roi(roi, vis)
    cv2.imshow('Visible light', vis)
    cv2.waitKey(1)
    #  loop: read new frame, collect rois, aggregated intensities and the intensities' stddev, display rois on frame
    frame_counter = 0
    JSONDictionary = {}
    # json_file
    with open("Output.json", "a") as f:
        f.write("[")
    for ii in range(frames_to_process):
        ret, frame = cap.read()
        vis, infra = stryker(frame)
        rois, agg_intensities, spread_intensities = vanilla.update(
            vis, infra)
        frame_counter += 1
        JSONDictionary = convert_to_dict(
            rois, agg_intensities, spread_intensities)
        JSONDictionary['frame_number'] = frame_counter
        print(f"\n{JSONDictionary}")
        json_file = convert_to_JSON_file(JSONDictionary)
        for roi in rois:
            plot_roi(roi, vis)
        cv2.imshow('Visible light', vis)
        cv2.waitKey(1)
    with open("Output.json", 'rb+') as f:
        f.seek(-3, os.SEEK_END)
        f.truncate()
    with open("Output.json", "a") as f:
        f.write("]")
