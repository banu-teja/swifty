document
  .getElementById("jobApplicationForm")
  .addEventListener("submit", async function (event) {
    // Make the function async
    event.preventDefault(); // Prevent the default form submission

    const form = event.target;
    const formData = new FormData(form); // Use FormData directly for fetch

    // Define the server endpoint URL - relative path since JS is served from same origin
    const submitUrl = "/api/submit-application";

    try {
      const response = await fetch(submitUrl, {
        method: "POST",
        body: formData, // Send FormData directly, fetch handles multipart/form-data
        // No 'Content-Type' header needed when sending FormData;
        // the browser sets it correctly with the boundary.
      });

      if (!response.ok) {
        // Try to get error details from the server response
        let errorDetail = `HTTP error! status: ${response.status}`;
        try {
          const errorData = await response.json();
          errorDetail += ` - ${errorData.detail || JSON.stringify(errorData)}`;
        } catch (e) {
          // If response is not JSON or empty
          errorDetail += ` - ${response.statusText}`;
        }
        throw new Error(errorDetail);
      }

      // Handle successful submission
      const result = await response.json();
      alert(
        `Success: ${result.message} (Data saved as ${result.application_file})`
      );
      form.reset(); // Clear the form after successful submission
    } catch (error) {
      console.error("Submission error:", error);
      alert(`Submission failed: ${error.message}`);
    }
  });
