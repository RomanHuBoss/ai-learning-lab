<?php
declare(strict_types=1);

$requestUri = $_SERVER['REQUEST_URI'] ?? '/api';
$target = 'http://127.0.0.1:18081' . $requestUri;
$requestHeaders = function_exists('getallheaders') ? getallheaders() : [];
$forwardHeaders = [];
foreach ($requestHeaders as $name => $value) {
    $lower = strtolower((string) $name);
    if (in_array($lower, ['content-type', 'authorization', 'accept'], true)) {
        $forwardHeaders[] = $name . ': ' . $value;
    }
}

$body = file_get_contents('php://input');
$curl = curl_init($target);
curl_setopt_array($curl, [
    CURLOPT_CUSTOMREQUEST => $_SERVER['REQUEST_METHOD'] ?? 'GET',
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HEADER => true,
    CURLOPT_HTTPHEADER => $forwardHeaders,
    CURLOPT_CONNECTTIMEOUT => 3,
    CURLOPT_TIMEOUT => 35,
]);
if ($body !== false && $body !== '') {
    curl_setopt($curl, CURLOPT_POSTFIELDS, $body);
}

$response = curl_exec($curl);
if ($response === false) {
    http_response_code(502);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['detail' => 'api_upstream_unavailable'], JSON_UNESCAPED_UNICODE);
    curl_close($curl);
    exit;
}

$headerSize = (int) curl_getinfo($curl, CURLINFO_HEADER_SIZE);
$statusCode = (int) curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
$responseHeaders = substr($response, 0, $headerSize);
$responseBody = substr($response, $headerSize);
curl_close($curl);

http_response_code($statusCode > 0 ? $statusCode : 502);
foreach (explode("\r\n", trim($responseHeaders)) as $headerLine) {
    if ($headerLine === '' || str_starts_with($headerLine, 'HTTP/')) {
        continue;
    }
    [$name, $value] = array_pad(explode(':', $headerLine, 2), 2, '');
    if (in_array(strtolower(trim($name)), ['content-type', 'content-length', 'location', 'cache-control'], true)) {
        header(trim($name) . ': ' . trim($value));
    }
}
echo $responseBody;
