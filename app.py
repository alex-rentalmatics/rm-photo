import streamlit as st
from PIL import Image
import piexif
import os
import datetime
import pandas as pd

def format_bytes(size):
    power = 1024
    n = 0
    units = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    while size > power and n < len(units) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"

def get_decimal_from_dms(dms, ref):
    try:
        degrees = dms[0][0] / dms[0][1]
        minutes = dms[1][0] / dms[1][1]
        seconds = dms[2][0] / dms[2][1]
        decimal = degrees + minutes / 60 + seconds / 3600
        if ref in ['S', 'W']:
            decimal *= -1
        return round(decimal, 8)
    except Exception as e:
        st.warning(f"Failed to convert GPS to decimal: {e}")
        return None

def extract_gps_coords(exif_dict):
    gps = exif_dict.get("GPS", {})
    try:
        lat = get_decimal_from_dms(
            gps[piexif.GPSIFD.GPSLatitude],
            gps[piexif.GPSIFD.GPSLatitudeRef].decode()
        )
        lon = get_decimal_from_dms(
            gps[piexif.GPSIFD.GPSLongitude],
            gps[piexif.GPSIFD.GPSLongitudeRef].decode()
        )
        return lat, lon
    except KeyError:
        return None, None

def get_primary_exif_values(exif_dict):
    ifd = exif_dict.get("0th", {})
    primary_info = {}
    tag_map = {
        piexif.ImageIFD.Make: "Make",
        piexif.ImageIFD.Model: "Model",
        piexif.ImageIFD.Orientation: "Orientation",
        piexif.ImageIFD.XResolution: "XResolution",
        piexif.ImageIFD.YResolution: "YResolution",
        piexif.ImageIFD.ResolutionUnit: "ResolutionUnit",
        piexif.ImageIFD.Software: "Software"
    }
    for tag_id, label in tag_map.items():
        value = ifd.get(tag_id)
        if isinstance(value, bytes):
            try:
                value = value.decode(errors="ignore")
            except:
                value = str(value)
        primary_info[label] = value
    return primary_info

def display_all_exif(exif_dict):
    for ifd_name, tag_data in exif_dict.items():
        # Skip non-dict sections like 'thumbnail' (which is bytes)
        if not isinstance(tag_data, dict) or not tag_data:
            continue

        st.subheader(f"{ifd_name} EXIF")

        tag_definitions = piexif.TAGS.get(ifd_name, {})

        for tag, value in tag_data.items():
            tag_info = tag_definitions.get(tag, {"name": f"Tag {tag}"})
            tag_name = tag_info["name"]

            if isinstance(value, bytes):
                try:
                    value = value.decode(errors="ignore")
                except:
                    value = str(value)

            st.write(f"**{tag_name}:** {value}")


def main():
    st.set_page_config(page_title="Image Metadata Tool", layout="centered")
    st.title("📷 Image Info & GPS Mapper")

    uploaded_file = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "tiff"])

    if uploaded_file:
        temp_path = "temp_image.jpg"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())

        image = Image.open(temp_path)
        exif_dict = piexif.load(image.info.get("exif", b""))

        tab1, tab2 = st.tabs(["🧭 Summary", "📑 More Metadata"])

        with tab1:
            st.image(image, caption="Uploaded Image", use_column_width=True)

            st.markdown("### 🗂️ Basic Info")
            st.write(f"**File Name:** {uploaded_file.name}")
            st.write(f"**Size:** {format_bytes(os.path.getsize(temp_path))}")
            st.write(f"**Modified:** {datetime.datetime.fromtimestamp(os.path.getmtime(temp_path)).strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"**Format:** {image.format}")
            st.write(f"**Dimensions:** {image.width} × {image.height}")
            st.write(f"**Mode:** {image.mode}")

            st.markdown("### 📸 Camera Info")
            primary = get_primary_exif_values(exif_dict)
            for label, value in primary.items():
                if value is not None:
                    st.write(f"**{label}:** {value}")

            st.markdown("### 🗺️ GPS Map")
            lat, lon = extract_gps_coords(exif_dict)
            if lat is not None and lon is not None:
                st.write(f"**Latitude:** {lat}")
                st.write(f"**Longitude:** {lon}")
                st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}))
            else:
                st.info("No GPS data found in this image.")

        with tab2:
            st.markdown("### 🧬 Full EXIF Metadata")
            if any(exif_dict.values()):
                display_all_exif(exif_dict)
            else:
                st.write("No EXIF data found.")

        os.remove(temp_path)

if __name__ == "__main__":
    main()
