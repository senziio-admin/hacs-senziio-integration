# HACS Senziio Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

Add [Senziio](https://senziio.com) integration to [Home Assistant](https://www.home-assistant.io)
via [HACS](https://hacs.xyz).

## Setup

### Install Integration via HACS

1. **Open Home Assistant UI**: Navigate to your Home Assistant instance in your web browser.

2. **Go to HACS**: Click on "HACS" (Home Assistant Community Store) in the sidebar.

3. **Add Custom Repository**: Click the three dots in the upper right corner and select *Custom Repositories*.

4. **Enter Repository Details**: Under "Custom repositories", enter the following details:

    - **Repository:** `https://github.com/senziio-admin/hacs-senziio-integration`
    - **Category:** Integration

5. **Add the Repository**: Click "Add" to save the custom repository in the HACS list.

6. **Go Back to HACS**: Return to the HACS listing page.

7. **Search for the Integration**: Type "Senziio" in the search bar.

8. **Download the Integration**: You should see the Senziio integration listed.
   From item 3 dots menu, click "Download" and follow any prompts to complete the process.

9. **Restart Home Assistant**: After the download is complete, restart Home Assistant to apply the changes.

10. **Reload the Page**: Reload the Home Assistant UI. Re-login may be required.

By following these steps, you will have successfully installed the Senziio integration via HACS.

### Adding a Device

1. **Open Home Assistant Settings**: Navigate to *Settings* > *Devices & Services* > *+ Add Integration*.

2. **Search for the Integration**: In the search bar, type "Senziio" and click on it when it appears in the list.

3. **Follow the Configuration Steps**: Enter the required information as prompted by the dialog. This may include the
     serial number, model and any other necessary details for your Senziio device. Follow the on-screen instructions
     to complete the configuration.

### Autodiscovery via Zeroconf

Devices also support autodiscovery via Zeroconf, which allows Home Assistant to automatically detect and configure
Senziio devices on your network. Ensure that your devices are connected to the same network as your Home Assistant
instance for autodiscovery to work.

### Additional Information

For more detailed information about integration usage, requirements, and troubleshooting, please refer to the
**[integration documentation](docs/README.md)**.

## Development

    python3.12 -m venv venv
    . venv/bin/activate
    pip install -r requirements_test.txt
    make test
