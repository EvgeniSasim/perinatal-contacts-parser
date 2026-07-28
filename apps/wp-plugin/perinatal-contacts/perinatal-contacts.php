<?php
/**
 * Plugin Name: Perinatal Contacts Directory
 * Description: Каталог перинатальных центров и ЖК через REST API
 * Version: 0.1.0
 * Author: EvgeniSasim
 * Text Domain: perinatal-contacts
 */

if (!defined('ABSPATH')) {
    exit;
}

define('PNC_OPTION_KEY', 'pnc_directory_settings');

function pnc_default_settings() {
    return array(
        'api_url' => 'http://localhost:8000/api/v1',
        'api_key' => '',
        'cache_ttl' => 300,
    );
}

add_action('admin_menu', function () {
    add_options_page(
        'Perinatal Contacts',
        'Perinatal Contacts',
        'manage_options',
        'pnc-directory',
        'pnc_render_settings_page'
    );
});

add_action('admin_init', function () {
    register_setting('pnc_directory', PNC_OPTION_KEY, array(
        'type' => 'array',
        'sanitize_callback' => 'pnc_sanitize_settings',
        'default' => pnc_default_settings(),
    ));
});

function pnc_sanitize_settings($input) {
    $out = pnc_default_settings();
    if (!is_array($input)) {
        return $out;
    }
    $out['api_url'] = esc_url_raw(isset($input['api_url']) ? $input['api_url'] : $out['api_url']);
    $out['api_key'] = sanitize_text_field(isset($input['api_key']) ? $input['api_key'] : '');
    $out['cache_ttl'] = absint(isset($input['cache_ttl']) ? $input['cache_ttl'] : 300);
    return $out;
}

function pnc_render_settings_page() {
    if (!current_user_can('manage_options')) {
        return;
    }
    $opts = wp_parse_args(get_option(PNC_OPTION_KEY, array()), pnc_default_settings());
    ?>
    <div class="wrap">
      <h1>Perinatal Contacts</h1>
      <form method="post" action="options.php">
        <?php settings_fields('pnc_directory'); ?>
        <table class="form-table">
          <tr>
            <th>API URL</th>
            <td><input type="url" name="<?php echo esc_attr(PNC_OPTION_KEY); ?>[api_url]" value="<?php echo esc_attr($opts['api_url']); ?>" class="regular-text" /></td>
          </tr>
          <tr>
            <th>API Key (optional for public)</th>
            <td><input type="text" name="<?php echo esc_attr(PNC_OPTION_KEY); ?>[api_key]" value="<?php echo esc_attr($opts['api_key']); ?>" class="regular-text" /></td>
          </tr>
          <tr>
            <th>Cache TTL (sec)</th>
            <td><input type="number" name="<?php echo esc_attr(PNC_OPTION_KEY); ?>[cache_ttl]" value="<?php echo esc_attr($opts['cache_ttl']); ?>" /></td>
          </tr>
        </table>
        <?php submit_button(); ?>
      </form>
      <p>Shortcode: <code>[pnc_directory]</code> — атрибуты <code>region</code>, <code>type</code>, <code>q</code>, <code>city</code>.</p>
    </div>
    <?php
}

function pnc_fetch_institutions($args) {
    $opts = wp_parse_args(get_option(PNC_OPTION_KEY, array()), pnc_default_settings());
    $query = array(
        'page_size' => 50,
    );
    foreach (array('region', 'type', 'q', 'city') as $key) {
        if (!empty($args[$key])) {
            $query[$key] = $args[$key];
        }
    }
    $url = trailingslashit($opts['api_url']) . 'institutions?' . http_build_query($query);
    $cache_key = 'pnc_' . md5($url);
    $cached = get_transient($cache_key);
    if ($cached !== false) {
        return $cached;
    }
    $headers = array('Accept' => 'application/json');
    if (!empty($opts['api_key'])) {
        $headers['X-API-Key'] = $opts['api_key'];
    }
    $response = wp_remote_get($url, array('timeout' => 15, 'headers' => $headers));
    if (is_wp_error($response)) {
        return array('error' => $response->get_error_message());
    }
    $code = wp_remote_retrieve_response_code($response);
    $body = json_decode(wp_remote_retrieve_body($response), true);
    if ($code !== 200 || !is_array($body)) {
        return array('error' => 'API error ' . intval($code));
    }
    set_transient($cache_key, $body, max(60, intval($opts['cache_ttl'])));
    return $body;
}

add_shortcode('pnc_directory', function ($atts) {
    $atts = shortcode_atts(array(
        'region' => '',
        'type' => '',
        'q' => '',
        'city' => '',
    ), $atts, 'pnc_directory');

    $q = isset($_GET['pnc_q']) ? sanitize_text_field(wp_unslash($_GET['pnc_q'])) : $atts['q'];
    $region = isset($_GET['pnc_region']) ? sanitize_text_field(wp_unslash($_GET['pnc_region'])) : $atts['region'];
    $type = isset($_GET['pnc_type']) ? sanitize_text_field(wp_unslash($_GET['pnc_type'])) : $atts['type'];
    $city = isset($_GET['pnc_city']) ? sanitize_text_field(wp_unslash($_GET['pnc_city'])) : $atts['city'];

    $data = pnc_fetch_institutions(array(
        'q' => $q,
        'region' => $region,
        'type' => $type,
        'city' => $city,
    ));

    ob_start();
    ?>
    <div class="pnc-directory">
      <form method="get" class="pnc-filters">
        <input type="search" name="pnc_q" value="<?php echo esc_attr($q); ?>" placeholder="Поиск" />
        <input type="text" name="pnc_region" value="<?php echo esc_attr($region); ?>" placeholder="Регион" />
        <input type="text" name="pnc_city" value="<?php echo esc_attr($city); ?>" placeholder="Город" />
        <input type="text" name="pnc_type" value="<?php echo esc_attr($type); ?>" placeholder="Тип" />
        <button type="submit">Найти</button>
      </form>
      <?php if (isset($data['error'])) : ?>
        <p class="pnc-error"><?php echo esc_html($data['error']); ?></p>
      <?php else : ?>
        <p>Найдено: <?php echo esc_html(isset($data['total']) ? $data['total'] : 0); ?></p>
        <ul class="pnc-list">
          <?php foreach ((isset($data['items']) ? $data['items'] : array()) as $item) : ?>
            <li>
              <strong><?php echo esc_html($item['name']); ?></strong><br />
              <?php echo esc_html($item['region'] . ', ' . $item['city']); ?><br />
              <?php echo esc_html($item['address']); ?><br />
              <?php if (!empty($item['phones'])) : ?>
                Тел.: <?php echo esc_html(implode(', ', $item['phones'])); ?><br />
              <?php endif; ?>
              <?php if (!empty($item['emails'])) : ?>
                Email: <?php echo esc_html(implode(', ', $item['emails'])); ?><br />
              <?php endif; ?>
              <?php if (!empty($item['chief_physician'])) : ?>
                Главный врач: <?php echo esc_html($item['chief_physician']); ?>
              <?php endif; ?>
            </li>
          <?php endforeach; ?>
        </ul>
      <?php endif; ?>
    </div>
    <?php
    return ob_get_clean();
});
