import numpy as np
from PIL import Image
import cv2

class ImageComparator:
    def __init__(self, threshold = 1):
        self.threshold = threshold
        #Threshold for differences (0-255)
        self.min_contour_area = 180
        self.kernel_erode = np.ones((2, 2), np.uint8)
        self.kernel_dilate = np.ones((2, 2), np.uint8)
    
    @staticmethod
    def load_image(image_input):
        #Load an image from a path or convert it if it's PIL.
        if isinstance(image_input, str): 
            img = cv2.imread(image_input)
            if img is None:
                raise ValueError(f"The image could not be loaded: {image_input}")
            return img
        elif isinstance(image_input, Image.Image):  
            return cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
        else:
            return image_input  

    def find_differences(self, img1_input, img2_input):
        """
        Detect differences in B/W images using only OpenCV: 
        1. Convert to grayscale (if they are not) 
        2. Binarize the images 
        3. Find absolute differences 
        4. Filter and highlight changes 
        5. Highlight different pixels in light green over the original color image
        """
        # 1) Load images

        img1 = self.load_image(img1_input)
        img2 = self.load_image(img2_input)

        merged_color_original = cv2.bitwise_and(img1, img2)
        cv2.imwrite("merged_color_original.png", merged_color_original)

        if img1.shape != img2.shape:
            print("Resizing img2....")
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]), interpolation=cv2.INTER_AREA)

        # 2) Ensure the images are binarized
        if len(img1.shape) > 2:
            img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        if len(img2.shape) > 2:
            img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # 3) Binarization
        _, bin1 = cv2.threshold(img1, 240, 255, cv2.THRESH_BINARY)
        cv2.imwrite("bin1.png", bin1)
        _, bin2 = cv2.threshold(img2, 240, 255, cv2.THRESH_BINARY)
        cv2.imwrite("bin2.png", bin2)

        # 4) Absolute difference
        diff_abs = cv2.absdiff(bin1, bin2)
        cv2.imwrite("absolute_differences.png", diff_abs)

        # Binarize image with absolute differences
        _, merged_color_original_bin = cv2.threshold(merged_color_original, 220, 255, cv2.THRESH_BINARY)
        cv2.imwrite("absolute_differences_binarized.png", merged_color_original_bin)

        # 5) Morphological operations to clean noise
        diff = cv2.dilate(diff_abs, self.kernel_erode, iterations=2)
        diff = cv2.erode(diff, self.kernel_erode, iterations=2)

        #Perform bitwise and of the two images
        print("Size of img1", bin1.shape)
        print("Size of img2", bin2.shape)

        merged_images = cv2.bitwise_and(bin1, bin2)
        cv2.imwrite("merged_images.png", merged_images)
        merged_inv = cv2.bitwise_not(merged_images)
        cv2.imwrite("merged_images_inv.png", merged_inv)
        #Convert merged_images from GRAY to BGR
        merged_color = cv2.cvtColor(merged_images, cv2.COLOR_GRAY2BGR)

        contours = []
        diff_coords = []

        # 6) Find significant contours
        contours, _ = cv2.findContours(diff, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        significant_contours = [c for c in contours if cv2.contourArea(c) >= self.min_contour_area]

        # 7) Extract coordinates from the contours
        diff_coords = []
        for contour in significant_contours:
            for point in contour:
                x, y = point[0]
                diff_coords.append((x, y))

        # 4. Create image in black
        filtered_diff = np.full_like(bin1, 255)
        print("Shape of abs changes img",filtered_diff.shape)

        # 5. Draw significant outlines in white
        cv2.drawContours(filtered_diff, significant_contours, -1, color=0, thickness=cv2.FILLED)

        # 6. Save or show final image of differences
        cv2.imwrite('filtered_differences.png', filtered_diff)

        # Save differences from image 1
        diff_processed_bin1 = cv2.absdiff(merged_images, bin2)
        cv2.imwrite("diff_for_bin1.png", diff_processed_bin1)

        diff_bin1 = cv2.dilate(diff_processed_bin1, self.kernel_erode, iterations=2)
        diff_bin1 = cv2.erode(diff_bin1, self.kernel_erode, iterations=2)

        # Save differences from image 2
        diff_processed_bin2 = cv2.absdiff(merged_images, bin1)
        cv2.imwrite("diff_for_bin2.png", diff_processed_bin2)

        diff_bin2 = cv2.dilate(diff_processed_bin2, self.kernel_erode, iterations=2)
        diff_bin2 = cv2.erode(diff_bin2, self.kernel_erode, iterations=2)
        cv2.imwrite("diff_mask_red.png", diff_bin2)

        #Invert differences from the first image
        inverted_bin2 = cv2.bitwise_not(diff_bin2)
        cv2.imwrite("diff_mask_green_inv.png", inverted_bin2)
        
        #img1 contours
        contours_bin1, _ = cv2.findContours(diff_bin1, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        significant_contours_bin1 = [c for c in contours_bin1 if cv2.contourArea(c) >= 1]

        #img2 contours
        contours_bin2, _ = cv2.findContours(diff_bin2, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        significant_contours_bin2 = [c for c in contours_bin2 if cv2.contourArea(c) >= 1]

        if len(significant_contours) > 100:
            return None,None, img1.shape
        
        #Draw img1 filtered contours
        filtered_bin1 = np.full_like(bin1, 255)
        cv2.drawContours(filtered_bin1, significant_contours_bin1, -1, color=0, thickness=cv2.FILLED)
        cv2.imwrite('filtered_bin1.png', filtered_bin1)
        
        #Draw img2 filtered contours
        filtered_bin2 = np.full_like(bin1, 255)
        cv2.drawContours(filtered_bin2, significant_contours_bin2, -1, color=0, thickness=cv2.FILLED)
        cv2.imwrite('filtered_bin2.png', filtered_bin2)

        # Create boolean mask for both images
        mask_img1_changes = filtered_bin1 == 0 # mask for deleted changes
        mask_img2_changes = filtered_bin2 == 0 #mask for added changes

        # Create green mask
        mask_color_green = np.zeros((filtered_diff.shape[0], filtered_diff.shape[1], 3), dtype=np.uint8)
        mask_color_green[mask_img2_changes] = [25, 115, 26]
        
        rows, cols = mask_color_green.shape[:2]
        
        # Move two pixels to adjust the image after applying drawContours
        dx, dy = -2, -2 
        M = np.float32([[1, 0, dx], [0, 1, dy]])

        mask_color_green = cv2.warpAffine(mask_color_green, M, (cols, rows))

        # OPTIONAL: Uncomment to save intermediate images to check the process
        #cv2.imwrite("mask_color_added.png", mask_color_green)
    
        #rgb_img2 = cv2.cvtColor(diff_processed_bin2, cv2.COLOR_GRAY2BGR)
        #highlighted_1 = cv2.addWeighted(merged_color, 1.0 , mask_color_green, 1.0, 0)
        #cv2.imwrite("mask_color_combined.png", highlighted_1)

        #highlighted_original1 = cv2.addWeighted(merged_color_original, 0.5, mask_color_green, 1.0, 0)
        #cv2.imwrite("mask_with_original.png", highlighted_original1)
        
        # A) Reload the original color image (not the B/W)
        img2_orig_color = self.load_image(img2_input)
        if len(img2_orig_color.shape) == 2:
            img2_orig_color = cv2.cvtColor(img2_orig_color, cv2.COLOR_GRAY2BGR)

        if filtered_diff.shape[:2] != img2_orig_color.shape[:2]:
            print(f"Redimensionando diff_processed de {filtered_diff.shape} a {img2_orig_color.shape[:2]}")
            filtered_diff = cv2.resize(
                filtered_diff,
                (img2_orig_color.shape[1], img2_orig_color.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )

        # Ensure the same shape for the images
        if mask_color_green.shape != img2_orig_color.shape:
            mask_color_green = cv2.resize(
                mask_color_green,
                (img2_orig_color.shape[1], img2_orig_color.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )

        # Combine with the original image using addWeighted
        highlighted_2 = cv2.addWeighted(merged_color, 1.0 , mask_color_green, 1.0, 0)

        # Use PIL to save with DPI
        im_pil = Image.fromarray(cv2.cvtColor(highlighted_2, cv2.COLOR_BGR2RGB))
        im_pil.save("highlighted_result_green.png", dpi=(300, 300))  # O el DPI que uses en tu PDF

        mask_color_red = np.zeros((filtered_diff.shape[0], filtered_diff.shape[1], 3), dtype=np.uint8)
        mask_color_red[mask_img1_changes] = [12, 12, 173]
        
        rows, cols = mask_color_red.shape[:2]
        mask_color_red = cv2.warpAffine(mask_color_red, M, (cols, rows))

        cv2.imwrite("mask_color_deleted.png", mask_color_red)
        # A) Load the original color image 
        img1_orig_color = self.load_image(img1_input)
        if len(img1_orig_color.shape) == 2:
            img1_orig_color = cv2.cvtColor(img1_orig_color, cv2.COLOR_GRAY2BGR)

        if filtered_diff.shape[:2] != img1_orig_color.shape[:2]:
            print(f"Redimensionando diff_processed de {filtered_diff.shape} a {img1_orig_color.shape[:2]}")
            filtered_diff = cv2.resize(
                filtered_diff,
                (img1_orig_color.shape[1], img1_orig_color.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )

        # Ensure the same shape for the images
        if mask_color_red.shape != img1_orig_color.shape:
            mask_color_red = cv2.resize(
                mask_color_red,
                (img1_orig_color.shape[1], img1_orig_color.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )
        
        # Combine with the original image using addWeighted
        highlighted_final = cv2.addWeighted(highlighted_2, 1.0, mask_color_red, 1.0, 0)

        # Use PIL to save DPI
        im_pil = Image.fromarray(cv2.cvtColor(highlighted_final, cv2.COLOR_BGR2RGB))
        im_pil.save("highlighted_result_red.png", dpi=(300, 300))  # O el DPI que uses en tu PDF

        # 9) Return coordinates of differences + highlighted image + shape
        return diff_coords, highlighted_final, img1.shape