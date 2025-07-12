class SenziioOverview extends HTMLElement {
  constructor() {
    super();
    this._shadow = this.attachShadow({ mode: "open" });
    this._config = {};
  }

  set panel(panel) {
    this._config = panel.config || {};
  }

  set hass(hass) {
    const list = Object.values(hass.states)
      .filter((st) =>
        st.entity_id.startsWith("sensor.senziio_") ||
        st.entity_id.startsWith("binary_sensor.senziio_")
      )
      .sort((a, b) =>
        a.attributes.friendly_name.localeCompare(b.attributes.friendly_name)
      )
      .map((st) => st.entity_id);

    const card = document.createElement("hui-entities-card");
    card.hass = hass;
    card.config = {
      type: "entities",
      title: "Senziio Overview",
      entities: list,
    };

    this._shadow.innerHTML = `
      <ha-top-app-bar-fixed>
        <span slot="title">Senziio Overview</span>
      </ha-top-app-bar-fixed>
      <div id="container" style="padding:16px;"></div>
    `;
    this._shadow.getElementById("container").appendChild(card);
  }
}

customElements.define("senziio-overview", SenziioOverview);
