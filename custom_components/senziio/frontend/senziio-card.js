/* senziio-data.js ─────────── super-simple list card */

import { LitElement, html } from
  "https://cdn.jsdelivr.net/npm/lit-element@4.1.1/+esm";

/* ▒ 1 – Register in the card picker (NO “custom:” prefix!) */
window.customCards = window.customCards || [];
window.customCards.push({
  type:        "senziio-data",
  name:        "Senziio Data Card",
  preview:     true,
  description: "Shows the Senziio entities you select, in that order"
});

/* ▒ 2 – Card implementation */
class SenziioDataCard extends LitElement {

  /* Let the built-in entities-card editor be our config UI */
  static getConfigElement() {
    return document.createElement("hui-entities-card-editor");
  }

  /* Preview in the picker */
  static getStubConfig() {
    return { entities: [] };
  }

  /* YAML validation */
  setConfig(config) {
    if (!Array.isArray(config.entities) || !config.entities.length) {
      throw new Error("senziio-data: define at least one entity");
    }
    this._config = config;
  }

  /* React to HA updates */
  set hass(hass) {
    this._hass = hass;
    this.requestUpdate();
  }

  /* Render the list */
  render() {
    if (!this._hass || !this._config) return html``;

    const items = this._config.entities
      .map(id => this._hass.states[id])
      .filter(Boolean)                     // drop unknown ids
      .map(st => html`
        <li>
          <strong>${st.attributes.friendly_name ?? st.entity_id}</strong>:
          ${st.state}
        </li>
      `);

    return html`
      <ha-card header="${this._config.title ?? 'Senziio Sensors'}">
        <ul style="list-style:none;margin:0;padding:8px">
          ${items}
        </ul>
      </ha-card>
    `;
  }

  getCardSize() {
    return this._config?.entities?.length || 1;
  }
}

/* ▒ 3 – Register the custom element */
customElements.define("senziio-data", SenziioDataCard);
