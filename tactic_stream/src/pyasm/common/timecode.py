###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

__all__ = ['TimeCode']




class TimeCode(object):

    def __init__(self, **kwargs):
        self.frames = kwargs.get("frames") or 0
        self.frames = float(self.frames)

        self.fps = kwargs.get("fps")
        if not self.fps:
            from pyasm.biz import ProjectSetting
            self.fps = ProjectSetting.get_value_by_key("fps")
            self.fps = int(self.fps or 24)
        if not self.fps:
            self.fps = 24

        self.fps = int(self.fps)
        if self.fps <= 0:
            raise ValueError('TimeCode fps must be positive')

        if not self.frames:
            timecode = kwargs.get("timecode")
            self.frames = self.calculate_frames(timecode, self.fps)

        # handle cases where frames has a decimal: ie: 400.4
        self.frames = int(float(self.frames))


    def get_frames(self):
        return self.frames


    def get_timecode(self, format='MM:SS:FF', fps=None):
        frames = self.frames
        if not fps:
            fps = self.fps

        hours = frames // (60*60*fps)
        minutes = (frames // (60*fps)) % 60
        seconds = ((frames // fps) % 60 ) % 60
        frames = frames % fps % 60 % 60

        if format == 'MM:SS:FF':
            timecode = "%0.2d:%0.2d:%0.2d" %(minutes, seconds, frames)
        elif format == 'MM:SS.FF':
            timecode = "%0.2d:%0.2d.%0.2d" %(minutes, seconds, frames)
        elif format == 'MM:SS':
            timecode = "%0.2d:%0.2d" %(minutes, seconds)
        elif format == 'HH:MM:SS:FF':
            timecode = "%0.2d:%0.2d:%0.2d:%0.2d" %(hours, minutes, seconds, frames)
        elif format == 'HH:MM:SS.FF':
            timecode = "%0.2d:%0.2d:%0.2d.%0.2d" %(hours, minutes, seconds, frames)
        elif format == 'HH:MM:SS':
            timecode = "%0.2d:%0.2d:%0.2d" %(hours, minutes, seconds)

        return timecode


    def calculate_frames(self, timecode, fps):
        if not timecode:
            return 0

        parts = timecode.split(":")
        if parts[-1].find(".") != -1:
            a, b = parts[-1].split(".")
            parts[-1] = a
            parts.append(b)

        # SS:FF
        if len(parts) == 2:
            seconds = int(parts[0])
            frames = int(parts[1])

            frames = frames + fps*seconds


        # MM:SS:FF
        elif len(parts) == 3:
            minutes = int(parts[0])
            seconds = int(parts[1])
            frames = int(parts[2])

            frames = frames + fps*( seconds + 60*(minutes) )

        # HH:MM:SS:FF
        elif len(parts) == 4:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            frames = int(parts[3])

            frames = frames + fps*( seconds + 60*(minutes + 60*hours) )

        else:
            raise ValueError('Timecode requires SS:FF, MM:SS:FF or HH:MM:SS:FF')
        return frames





    def __add__(self, timecode):

        if isinstance(timecode, int):
            frames = timecode
        else:
            if isinstance(timecode, TimeCode):
                t = timecode
            else:
                t = TimeCode(timecode=timecode, fps=self.fps)
            frames = t.get_frames()
            
        frames = frames + self.get_frames()

        t2 = TimeCode(frames=frames, fps=self.fps)
        return t2



    def __sub__(self, timecode):

        if isinstance(timecode, int):
            frames = timecode
        else:
            if isinstance(timecode, TimeCode):
                t = timecode
            else:
                t = TimeCode(timecode=timecode, fps=self.fps)
            frames = t.get_frames()

        frames = self.get_frames() - frames

        t2 = TimeCode(frames=frames, fps=self.fps)
        return t2

