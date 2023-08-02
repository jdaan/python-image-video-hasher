from PIL import Image
import os
import imagehash
import distance
import pytesseract
import database
import numpy as np


class ImageProcessor:
    """
    HALLO Image processor
    """

    def is_image(self, filename):
        """
        Check if given filename is an image
        noinspection PyMethodMayBeStatic
        :param filename:
        :return:
        """

        f = filename.lower()
        return f.endswith(".png") or f.endswith(".jpg") or \
               f.endswith(".jpeg") or f.endswith(".bmp") or \
               f.endswith(".gif") or '.jpg' in f or f.endswith(".svg")

    def create_hash(self, image):
        """
        Create 3 hashes of the image
        noinspection PyMethodMayBeStatic
        :param image:
        :return:
        """

        hash = str(imagehash.phash(image, 16))
        dhash = str(imagehash.dhash(image, 16))
        dhash_v = str(imagehash.dhash_vertical(image, 16))

        return [hash, dhash, dhash_v]

    def image_to_text(self, image):
        """
        Use OCR to read the text on the image
        used for scanning memes
        noinspection PyMethodMayBeStatic
        :param image:
        :return:
        """

        return pytesseract.image_to_string(image)

    def calculate_ham_dist(self, hash_str, hash_str2):
        """
        Calculates the hamming distance of two strings
        and converts it into a similarity percentage
        noinspection PyMethodMayBeStatic
        :param hash_str:
        :param hash_str2:
        :return:
        """

        dist = distance.hamming(hash_str, hash_str2)

        percentage = round((100 - ((64 / 100) * dist)), 2)

        return percentage

    def compare_image(self, hashes, image_hash):
        """
        Function will create 3 different hashes of the given image and
        calculate the hamming distance between the given hashes the result
        will be an array of the similarity percentage of each hash
        :param hashes:
        :param image_hash:
        :return:
        """

        phash_dist = self.calculate_ham_dist(hashes[0], image_hash[0])
        dhash_dist = self.calculate_ham_dist(hashes[1], image_hash[1])
        dhash_v_dist = self.calculate_ham_dist(hashes[2], image_hash[2])

        # Calculate total percentage of all hashes
        total_percentage = round((phash_dist + dhash_dist + dhash_v_dist) / 3)

        return [phash_dist, dhash_dist, dhash_v_dist, total_percentage]

    # noinspection PyMethodMayBeStatic
    def compare_text(self, text, text2):
        """
        Calculate the similarity percentage between two strings using levenshtein
        :param text:
        :param text2:
        :return:
        """

        if text is None:
            text = ""

        if text2 is None:
            text2 = ""

        # Get the length of the longest string
        text_len = max([len(text), len(text2)])
        # Calculate the difference between the two texts
        text_dist = distance.levenshtein(text, text2)
        # Convert the difference into a percentage
        percentage = round((100 - ((text_len / 100) * text_dist)), 2)

        return percentage

    def add_image(self, image_path, message_id):
        """
        Generate hashes of the given image and add them to the DB
        :param image_path:
        :param message_id:
        :return:
        """

        image = Image.open(image_path)
        image_hashes = self.create_hash(image)
        image_text = self.image_to_text(image)
        image_text = (''.join([c for c in image_text if c not in [' ', '\t', '\n']]))

        res = database.add_image(
            image_hashes[0],
            image_hashes[1],
            image_hashes[2],
            os.path.basename(image_path),
            message_id,
            image_text
        )

        return res

    def sort_res_array(self, x, column=None, flip=False):
        """
        Will sort the response array based on the given column and order
        :param x:
        :param column:
        :param flip:
        :return:
        """

        x = x[np.argsort(x[:, column])]
        if flip:
            x = np.flip(x, axis=0)
        return x

    def repost_check(self, image, total_img_perc, txt_perc):
        """
        Function will compare all hashes in the DB with the hashes of the given image
        it will then return all images meeting the given threshold
        :param image:
        :param total_img_perc:
        :param txt_perc:
        :return:
        """

        image_hashes = self.create_hash(image)
        all_images = database.get_all_images()

        found = []

        if txt_perc > 0:
            # OCR the image for any text
            image_text = self.image_to_text(image)
            # Remove any spaces, enters etc.
            image_text = (''.join([c for c in image_text if c not in [' ', '\t', '\n']]))
        else:
            image_text = ""

        for img in all_images:
            dist_perc_res = self.compare_image([img[0], img[1], img[2]], image_hashes)

            # Check if the total percentage is greater than the minimum required value
            if dist_perc_res[3] > total_img_perc:
                if txt_perc > 0:
                    dist_perc_txt = self.compare_text(image_text, img[6])

                    # Check if the text similarity percentage is greater than the set threshold
                    if dist_perc_txt > txt_perc:
                        return_data = img + (dist_perc_res[3], dist_perc_txt)
                        found.append(return_data)
                else:
                    return_data = img + (dist_perc_res[3], 0)
                    found.append(return_data)

        if len(found) > 0:
            found_arr = np.asarray(found)
            res_array = self.sort_res_array(found_arr, column=7, flip=True).tolist()
            return res_array
        else:
            return False
