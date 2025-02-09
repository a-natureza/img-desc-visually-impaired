import cv2
import os
from ultralytics import YOLO
import shutil
from PIL import Image
import numpy as np
from sklearn.cluster import KMeans
import webcolors
from. import heat_map as hm
from. import inference_weather as wm
import glob

"""
def closest_colour(requested_colour):
    min_colours = {}
    for name in webcolors.names("css3"):
        r_c, g_c, b_c = webcolors.name_to_rgb(name)
        rd = (r_c - requested_colour[0]) ** 2
        gd = (g_c - requested_colour[1]) ** 2
        bd = (b_c - requested_colour[2]) ** 2
        min_colours[(rd + gd + bd)] = name
    return min_colours[min(min_colours.keys())]

def get_colour_name(requested_colour):
    try:
        #print(f"requested color: {requested_colour}")
        closest_name = actual_name = webcolors.rgb_to_name(requested_colour)
    except ValueError:
        closest_name = closest_colour(requested_colour)
        actual_name = None
    return actual_name, closest_name

def color_distance(color1, color2):
    return np.sqrt(np.sum((np.array(color1) - np.array(color2)) ** 2))

def combine_similar_colors(cluster_centers, labels, counts, threshold=70):
    # Initialize lists to store combined colors and their counts
    combined_colors = []
    combined_counts = []

    # Iterate over each cluster center
    for i, center in enumerate(cluster_centers):
        # Check if this color has already been combined
        if any(color_distance(center, existing_color) < threshold for existing_color in combined_colors):
            # Find index of the similar color group
            similar_index = next(
                idx for idx, existing_color in enumerate(combined_colors)
                if color_distance(center, existing_color) < threshold
            )
            combined_counts[similar_index] += counts[i]
        else:
            # Add new color to the list
            combined_colors.append(center)
            combined_counts.append(counts[i])

    return np.array(combined_colors), np.array(combined_counts)

def compute_mean_color_region(image_path, x1, y1, x2, y2, n_clusters=3, threshold=70):
    from PIL import Image
    from collections import Counter
    
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img_array = np.array(img)
        region = img_array[int(y1):int(y2), int(x1):int(x2)]
        pixels = region.reshape(-1, 3)
        
        kmeans = KMeans(n_clusters=n_clusters)
        kmeans.fit(pixels)

        pixel_labels = kmeans.labels_
        cluster_centers = kmeans.cluster_centers_
        unique_labels, counts = np.unique(pixel_labels, return_counts=True)

        # Combine similar colors
        combined_colors, combined_counts = combine_similar_colors(cluster_centers, pixel_labels, counts, threshold)
        
        # Find the dominant color
        dominant_color_index = np.argmax(combined_counts)
        dominant_color = combined_colors[dominant_color_index].astype(int)

        # Return the dominant color as a tuple (R, G, B)
        return get_colour_name(tuple(dominant_color))[1]"""

def closest_colour(requested_colour):
    min_colours = {}
    for name in webcolors.names("css3"):
        r_c, g_c, b_c = webcolors.name_to_rgb(name)
        rd = (r_c - requested_colour[0]) ** 2
        gd = (g_c - requested_colour[1]) ** 2
        bd = (b_c - requested_colour[2]) ** 2
        min_colours[(rd + gd + bd)] = name
    return min_colours[min(min_colours.keys())]

def get_colour_name(requested_colour):
    try:
        #print(f"requested color: {requested_colour}")
        closest_name = actual_name = webcolors.rgb_to_name(requested_colour)
    except ValueError:
        closest_name = closest_colour(requested_colour)
        actual_name = None
    return actual_name, closest_name

def map_to_nearest_color(pixel, color_map):
    # Find the nearest color in the color_map
    pixel = np.array(pixel)
    distances = np.linalg.norm(color_map - pixel, axis=1)
    return color_map[np.argmin(distances)]

def combine_similar_colors(cluster_centers, pixel_labels, counts, threshold):
    # Combine colors that are close to each other into one representative color
    color_map = np.array(cluster_centers)
    new_colors = []
    new_counts = []
    
    for i, count in enumerate(counts):
        color = cluster_centers[i]
        assigned = False
        for j, new_color in enumerate(new_colors):
            if np.linalg.norm(new_color - color) < threshold:
                new_counts[j] += count
                assigned = True
                break
        if not assigned:
            new_colors.append(color)
            new_counts.append(count)
    
    return np.array(new_colors), np.array(new_counts)

def assign_to_dominant_color(region, color_map):
    # Map all pixels to the nearest color in the color_map
    reshaped_region = region.reshape(-1, 3)
    mapped_region = np.array([map_to_nearest_color(pixel, color_map) for pixel in reshaped_region])
    return mapped_region.reshape(region.shape)

def compute_mean_color_region(image_path, x1, y1, x2, y2, n_clusters=3, threshold=70):
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img_array = np.array(img)
        region = img_array[int(y1):int(y2), int(x1):int(x2)]
        pixels = region.reshape(-1, 3)
        
        kmeans = KMeans(n_clusters=n_clusters)
        kmeans.fit(pixels)

        pixel_labels = kmeans.labels_
        cluster_centers = kmeans.cluster_centers_
        unique_labels, counts = np.unique(pixel_labels, return_counts=True)

        # Combine similar colors
        combined_colors, combined_counts = combine_similar_colors(cluster_centers, pixel_labels, counts, threshold)
        
        # Assign similar colors to the dominant colors
        mapped_region = assign_to_dominant_color(region, combined_colors)
        mapped_pixels = mapped_region.reshape(-1, 3)
        
        kmeans_final = KMeans(n_clusters=n_clusters)
        kmeans_final.fit(mapped_pixels)

        final_pixel_labels = kmeans_final.labels_
        final_cluster_centers = kmeans_final.cluster_centers_
        final_unique_labels, final_counts = np.unique(final_pixel_labels, return_counts=True)

        # Combine similar colors again if needed
        final_combined_colors, final_combined_counts = combine_similar_colors(final_cluster_centers, final_pixel_labels, final_counts, threshold)
        
        # Find the dominant color
        dominant_color_index = np.argmax(final_combined_counts)
        dominant_color = final_combined_colors[dominant_color_index].astype(int)

        # Return the dominant color as a tuple (R, G, B)
        return get_colour_name(tuple(dominant_color))[1]

def extract_entities_image(sourcePath:str):

    model = YOLO("yolov8x.pt", task="detect")
    cd = os.getcwd() 

    original_path = os.path.dirname(sourcePath)
    results = model(sourcePath, save = True, project=original_path)

    #--------------------------------------
    # Get the path of the saved results from the results object'
    # Find all directories matching the pattern
    directories = glob.glob(os.path.join(original_path, 'predict*'))
    
    # Return the most recent directory and add original. filename eg. processed/predict1/image.png
    if directories:
        saved_path =  max(directories, key=os.path.getmtime)
        saved_path = os.path.join(saved_path, os.path.basename(sourcePath))
    #----------------------------------------

    dimensions = "Image dimensions: (width=" + str(cv2.imread(sourcePath).shape[1]) + ") x (height="+ str(cv2.imread(sourcePath).shape[0]) + ")\n"
    information = []
    heat_map_path = hm.heat_map(sourcePath)
    heat_map_array = hm.load_npy(heat_map_path)
    max_deepth = "Max deepth: " + str(heat_map_array.max()) + "\n"
    min_deepth = "Min deepth: " + str(heat_map_array.min()) + "\n"
    weather = wm.inference_image(sourcePath)

    for result in results:
        boxes = result.boxes  # This contains the bounding boxes for detected objects
        # Indent the following code block
        for box in boxes:
            # Extract the bounding box coordinates
            x1, y1, x2, y2 = box.xyxy[0].tolist()  # top-left and bottom-right corners
            
            # Extract other information
            confidence = box.conf[0].item()  # confidence score
            if confidence > 0.75:
                class_id = box.cls[0].item()  # class id
                class_name = model.names[int(class_id)]  # class name
                
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                color = compute_mean_color_region(sourcePath,x1,y1,x2,y2)
                # Print or store the results
                information.append(f"{color} {class_name} at coordinates: [{x1}, {y1}, {x2}, {y2}] with heat deepth of {heat_map_array[center_y][center_x]} in the centre of the image\n")
    
    carpeta = os.path.join(cd, '__pycache__')
    if os.path.isdir(carpeta):
        shutil.rmtree(carpeta)
        
    return dimensions, max_deepth, min_deepth, weather, information, saved_path     # Also return the path for the saved object detection image