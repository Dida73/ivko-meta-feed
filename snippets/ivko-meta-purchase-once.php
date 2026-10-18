<?php
/**
 * Ивко: една сървърна покупка към Meta за една поръчка.
 * Само спира ПОВТОРНО изпращане на същата поръчка. Не пипа нищо друго.
 * За спиране: изключи фрагмента във WPCode.
 */
add_filter( 'pre_http_request', function ( $pre, $args, $url ) {
	try {
		if ( false !== $pre || ! is_string( $url ) || false === strpos( $url, 'graph.facebook.com' ) || false === strpos( $url, '/events' ) ) {
			return $pre;
		}
		$body = isset( $args['body'] ) ? $args['body'] : '';
		if ( ! is_string( $body ) || false === strpos( $body, '"Purchase"' ) ) {
			return $pre;
		}
		$json = json_decode( $body, true );
		if ( ! is_array( $json ) || empty( $json['data'] ) || ! is_array( $json['data'] ) ) {
			return $pre;
		}
		$keep    = array();
		$dropped = 0;
		foreach ( $json['data'] as $ev ) {
			$order_id = ( is_array( $ev ) && isset( $ev['event_name'], $ev['custom_data']['order_id'] ) && 'Purchase' === $ev['event_name'] ) ? (int) $ev['custom_data']['order_id'] : 0;
			if ( $order_id > 0 ) {
				// add_option връща false, ако записът вече съществува = тази поръчка вече е пратена.
				if ( ! add_option( 'ivko_fb_purchase_sent_' . $order_id, time(), '', 'no' ) ) {
					$dropped++;
					continue;
				}
			}
			$keep[] = $ev;
		}
		if ( 0 === $dropped ) {
			return $pre;
		}
		if ( empty( $keep ) ) {
			// Нищо ново за пращане: връщаме "успех", без да викаме Meta.
			return array(
				'headers'  => array(),
				'body'     => '{"events_received":0,"messages":[],"fbtrace_id":"ivko-skipped-duplicate"}',
				'response' => array( 'code' => 200, 'message' => 'OK' ),
				'cookies'  => array(),
				'filename' => null,
			);
		}
		// Има и други събития в пакета: пращаме само новите.
		return wp_remote_post( $url, array_merge( $args, array( 'body' => wp_json_encode( array_merge( $json, array( 'data' => $keep ) ) ) ) ) );
	} catch ( \Throwable $e ) {
		return $pre; // при всяка грешка не правим нищо
	}
}, 10, 3 );
