document.getElementById('uploadButton').addEventListener('click', async () => {
    const imageUpload = document.getElementById('imageUpload');
    const firstApiResponseDisplay = document.getElementById('firstApiResponse');
    const imagePathDisplay = document.getElementById('imagePath');
    const secondApiRequestPayloadDisplay = document.getElementById('secondApiRequestPayload');
    const apiResponseDisplay = document.getElementById('apiResponse');

    // Clear previous content
    firstApiResponseDisplay.textContent = '';
    imagePathDisplay.textContent = '';
    secondApiRequestPayloadDisplay.textContent = '';
    apiResponseDisplay.textContent = '';

    if (imageUpload.files.length === 0) {
        apiResponseDisplay.textContent = 'Please select an image first.';
        return;
    }

    const imageFile = imageUpload.files[0];
    const formData = new FormData();
    formData.append('IMAGE', imageFile);
    formData.append('MODID', 'PHOTOSEARCH');
    formData.append('IMAGE_TYPE', 'ImgSearch');
    formData.append('USR_ID', '18882828');
    formData.append('UPLOADED_BY', '94011');

    apiResponseDisplay.textContent = 'Uploading image to first API...';

    try {
        // First API call
        const response1 = await fetch('https://uploading-external.imimg.com/uploadimage', {
            method: 'POST',
            body: formData
        });

        const responseData1 = await response1.json();

        // Display the full first API response
        firstApiResponseDisplay.textContent = JSON.stringify(responseData1, null, 2);

        // Access the nested Image_Original_Path
        const imageOriginalPath = responseData1.Data?.AwsPath?.Image_Original_Path;

        if (imageOriginalPath) {
            imagePathDisplay.textContent = imageOriginalPath;
            apiResponseDisplay.textContent = 'Image uploaded. Now preparing to call second API via proxy...';

            // Second API call payload
            const secondApiPayload = {
                "Case": "normal",
                "Image_url": imageOriginalPath,
                "glid": "208238145",
                "modid": "photo_search",
                "ip": "103.226.203.223",
                "usr_id": "208238145",
                "add_input": {},
                "urlmet": "prod",
                "hybrid": "1",
                "object_detection": "1"
            };

            // Display the second API request payload
            secondApiRequestPayloadDisplay.textContent = JSON.stringify(secondApiPayload, null, 2);
            apiResponseDisplay.textContent = 'Calling second API via proxy...';

            // MODIFIED: Send request to the Python proxy endpoint
            const response2 = await fetch('/proxy-api', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(secondApiPayload)
            });

            const responseData2 = await response2.json();
            apiResponseDisplay.textContent = JSON.stringify(responseData2, null, 2);

        } else {
            apiResponseDisplay.textContent = 'Error: Image_Original_Path not found in the first API response (or is empty).';
            imagePathDisplay.textContent = '---'; // Indicate that the path was not found
        }

    } catch (error) {
        console.error('Error during API calls:', error);
        apiResponseDisplay.textContent = `An error occurred: ${error.message}`;
    }
});