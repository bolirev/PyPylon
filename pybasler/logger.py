import lz4.frame
import os
from multiprocessing import Process
import numpy as np


class LZ4DiffLogger(Process):
    """ LZ4DiffLogger class appends datas to an archive file


    """

    def __init__(self, m, ready_queue, nimel):
        super(LZ4DiffLogger, self).__init__()
        self.m = m
        self.ready_queue = ready_queue
        self.nimel = nimel
        self.__filename = None
        self.__threshold = None

    @property
    def filename(self):
        return self.__filename

    @filename.setter
    def filename(self, name):
        if not isinstance(name, str):
            raise TypeError('Filename should be a string')
        if os.path.exists(name):
            raise IOError('File already exist')
        self.__filename = name

    @property
    def threshold(self):
        return self.__threshold

    @threshold.setter
    def threshold(self, th):
        if not isinstance(th, self.buffer_type):
            raise TypeError('Threshold is not {}', self.buffer_type)
        self.__threshold = th

    def run(self):
        maxval = np.iinfo(self.buffer_type).max
        image = np.frombuffer(self.m.get_obj(), dtype=self.buffer_type)
        nimel = self.nimel
        text_file = open(self.filename+'.log', "w")
        with lz4.frame.open(self.filename,
                            mode='ab',
                            auto_flush=False) as fp:
            frame_i = 0
            while True:
                rot_i = self.ready_queue.get()
                if rot_i is None:
                    # A Poison pill has been send,
                    # so we quit the loop
                    break
                if rot_i == 0:
                    # Everytime the rot_i is zero,
                    # the full image is saved
                    im = image[rot_i*nimel:(rot_i+1)*nimel]
                    msg = 'FULL,{:016d}'.format(frame_i)
                    print(msg)  # Nice to see whats's happening
                    text_file.write(msg)  # logging
                    old_image = im.copy()
                elif rot_i == -1:
                    # A frame has been droped
                    msg = "DROP,{:016d}".format(frame_i)
                    print(msg)
                    text_file.write(msg)
                    frame_i += 1
                    continue
                else:
                    # A frame has been correctly received
                    # Calculate difference and threshold
                    im = image[(rot_i*nimel):(rot_i+1)*nimel] - old_image
                    im[im < self.__threshold] = 0
                    # because 1-4 -> 255-3
                    im[im > (maxval-self.__threshold)] = 0
                fp.write(im)
                frame_i += 1
        text_file.close()
