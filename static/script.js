function showBankStatus() {
    const statusMessage = document.getElementById("status-message");

    statusMessage.innerHTML = "Banking application is running and connected with backend service.";
}

console.log("CloudBank Flask Banking App Loaded Successfully");

document.addEventListener("DOMContentLoaded", function () {
    const forms = document.querySelectorAll("form");

    forms.forEach(function (form) {
        form.addEventListener("submit", function () {
            const button = form.querySelector("button");

            if (button) {
                button.innerHTML = "Processing...";
                button.disabled = true;
            }
        });
    });
});