import exifread
import pymediainfo
from datetime import datetime
import os
import sys


class Image_Location():
    def __init__(self, images_path):
        self.imgs_path = images_path

    def get_image_exif(self):
        for entry in os.listdir(self.imgs_path):
            entry = os.path.join(self.imgs_path, entry)
            if os.path.isfile(entry) and entry.endswith(".jpg"):
                try:
                    with open(entry, 'rb') as img_read:
                        img_exif = exifread.process_file(img_read)

                    suffix = "jpg"
                    take_time = img_exif.get("EXIF DateTimeOriginal", None)
                    take_time = img_exif.get("EXIF DateTimeDigitized", None) if take_time is None else take_time
                    if take_time is None:
                        print("\t*****Can't find picture date for %s", entry)
                        continue

                    take_time = datetime.strptime(take_time.printable, "%Y:%m:%d %H:%M:%S").strftime("%Y%m%d_%H%M%S")
                    pic_name = "mmexport_%s.%s" % (take_time, suffix)
                    print("Rename %s => %s", entry, pic_name)
                    # os.rename(entry, pic_name)
                except Exception as e:
                    print("Exception: %s", str(e))

    def get_video_info(self):
        for entry in os.listdir(self.imgs_path):
            entry = os.path.join(self.imgs_path, entry)
            if os.path.isfile(entry) and entry.endswith(".mp4"):
                try:
                    img_exif = pymediainfo.MediaInfo.parse(entry)
                    take_time = img_exif.general_tracks[0].encoded_date
                    take_time = img_exif.general_tracks[0].tagged_date if not take_time else take_time
                    print(entry, "Datetime: ", take_time)
                except Exception as e:
                    print("Exception: %s", str(e))


if __name__ == '__main__':
    args = sys.argv
    if len(args) != 2 or not os.path.isdir(sys.argv[1]):
        print("Usage: %s <images path>", sys.argv[0])
        exit(-1)

    location = Image_Location(sys.argv[1])
    location.get_image_exif()
    # location.get_video_info()
