import streamlit as st
from PIL import Image
import piexif
import io
import geocoder

def get_exif_dict(image):
    exif_data = image.info.get('exif')
    if exif_data:
        return piexif.load(exif_data)
    return {}

def save_image_with_exif(image, exif_dict):
    try:
        exif_bytes = piexif.dump(exif_dict)
        byte_io = io.BytesIO()
        image.save(byte_io, format='JPEG', exif=exif_bytes)
        byte_io.seek(0)
        return byte_io
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde de l'image avec les métadonnées: {e}")
        raise

def convert_to_proper_type(value, tag, ifd_name):
    try:
        if tag in piexif.TAGS[ifd_name]:
            type_name = piexif.TAGS[ifd_name][tag]["type"]
            if type_name in (piexif.TYPES.Byte, piexif.TYPES.Short, piexif.TYPES.Long,
                             piexif.TYPES.SByte, piexif.TYPES.SShort, piexif.TYPES.SLong):
                return int(value)
            elif type_name == piexif.TYPES.Ascii:
                return value.encode('utf-8')
            elif type_name in (piexif.TYPES.Rational, piexif.TYPES.SRational):
                num, denom = map(int, value.strip('()').split(','))
                return (num, denom)
            elif type_name == piexif.TYPES.Undefined:
                return bytes(value, 'utf-8')
        return value
    except Exception as conversion_error:
        st.error(f"Erreur de conversion de la valeur '{value}' pour le tag '{tag}': {conversion_error}")
        return value

def get_current_gps():
    g = geocoder.ip('me')
    if g.ok:
        lat, lng = g.latlng
        return lat, lng
    else:
        st.error("Impossible de récupérer les coordonnées GPS actuelles.")
        return None, None

def float_to_rational(value):
    """ Convert a float to an EXIF rational tuple (numerator, denominator) """
    if value is None:
        return (0, 1)
    value = abs(value)
    denom = 10000000  # This gives a good precision
    num = int(value * denom)
    return (num, denom)

def gps_latitude_longitude(lat, lng):
    """ Convert latitude and longitude to EXIF GPS format """
    return {
        piexif.GPSIFD.GPSLatitudeRef: 'N' if lat >= 0 else 'S',
        piexif.GPSIFD.GPSLatitude: [float_to_rational(abs(lat)), float_to_rational((abs(lat) * 60) % 60), float_to_rational((abs(lat) * 3600) % 60)],
        piexif.GPSIFD.GPSLongitudeRef: 'E' if lng >= 0 else 'W',
        piexif.GPSIFD.GPSLongitude: [float_to_rational(abs(lng)), float_to_rational((abs(lng) * 60) % 60), float_to_rational((abs(lng) * 3600) % 60)]
    }

st.title('Éditeur de métadonnées EXIF')

uploaded_file = st.file_uploader("Choisissez une image", type=["jpg", "jpeg"])
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='Image téléchargée', use_column_width=True)

    exif_dict = get_exif_dict(image)

    if exif_dict:
        st.subheader('Modifier les métadonnées EXIF')
        modified_exif = {}
        with st.form("exif_form"):
            for ifd_name, ifd_dict in exif_dict.items():
                st.write(f"### {ifd_name}")
                modified_exif[ifd_name] = {}
                if isinstance(ifd_dict, dict):
                    for tag, value in ifd_dict.items():
                        tag_name = piexif.TAGS[ifd_name][tag]['name']
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        new_value = st.text_input(f"{tag_name} ({ifd_name}_{tag})", str(value), key=f"{ifd_name}_{tag}")
                        modified_exif[ifd_name][tag] = convert_to_proper_type(new_value, tag, ifd_name)
                else:
                    st.warning(f"IFD {ifd_name} contient des données non prises en charge.")
            form_submitted = st.form_submit_button("Sauvegarder les modifications")
            
            if form_submitted:
                try:
                    st.write("Données EXIF modifiées :")
                    st.json(modified_exif)  # Debugging information
                    byte_io = save_image_with_exif(image, modified_exif)
                    st.download_button(
                        label="Télécharger l'image avec les métadonnées modifiées",
                        data=byte_io,
                        file_name="image_modifiee.jpg",
                        mime="image/jpeg"
                    )
                except Exception as save_error:
                    st.error(f"Erreur lors de la sauvegarde de l'image avec les métadonnées modifiées: {save_error}")
    
        # Ajouter un bouton pour mettre à jour les données GPS en dehors du formulaire
        st.subheader('Mettre à jour les données GPS actuelles')
        lat, lng = get_current_gps()
        if lat and lng:
            st.write(f"Latitude actuelle : {lat}")
            st.write(f"Longitude actuelle : {lng}")
            
            if st.button('Mettre à jour les tags GPS'):
                gps_data = gps_latitude_longitude(lat, lng)
                if piexif.GPSIFD not in modified_exif:
                    modified_exif[piexif.GPSIFD] = {}
                modified_exif[piexif.GPSIFD].update(gps_data)
                st.write("Tags GPS mis à jour dans le formulaire.")
            
            if form_submitted:
                try:
                    st.write("Données EXIF modifiées avec GPS :")
                    st.json(modified_exif)  # Debugging information
                    byte_io = save_image_with_exif(image, modified_exif)
                    st.download_button(
                        label="Télécharger l'image avec les métadonnées modifiées",
                        data=byte_io,
                        file_name="image_modifiee.jpg",
                        mime="image/jpeg"
                    )
                except Exception as save_error:
                    st.error(f"Erreur lors de la sauvegarde de l'image avec les métadonnées modifiées: {save_error}")
    else:
        st.write("Cette image ne contient pas de métadonnées EXIF.")
