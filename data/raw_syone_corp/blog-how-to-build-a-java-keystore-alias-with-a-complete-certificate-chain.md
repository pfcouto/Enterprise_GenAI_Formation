# How to build a Java Keystore alias with a complete certificate chain

Source: https://www.syone.com/blog/how-to-build-a-java-keystore-alias-with-a-complete-certificate-chain
Section: blog
Summary: Step-by-step guide to build a Java Keystore alias with the complete certificate chain using OpenSSL and keytool, including PKCS12 vs JKS and common errors.
Scraped: 2026-10-20

14.05.2020 - Maximiano Tomé · 6 min read

As a Systems Administrator, updating Java Keystores is something that I am in charge of from time to time and honestly... it always gives me a headache!!

To get over this problem, I wrote this cheat sheet, so I never have to worry about it again! And now I’m sharing it with you.

more This article is a guide that will help you build a Java Keystore alias with a complete certificate chain, aggregating it to your main domain certificate, rather than importing several aliases with the intermediary certificate and root. This is very useful when you have external entities or commands that certify or generate your entire certificate chain.

### Key Takeaways

- A Java Keystore alias should contain the full certificate chain (domain, intermediate and root), not just the domain certificate.
- The trick is in the first step: concatenate the certificates with cat , in the right order.
- Convert the chain and private key to PKCS12 with OpenSSL, using -name to set the alias.
- Since Java 9, PKCS12 is the default keystore format; use JKS only when a legacy system requires it.
- Confirm the result with keytool -list -v : the chain length should match the number of certificates.

But first... a quick intro:

With the rising security threats, software environments continually increase their security measures, which means developers more often than not have to deal with digital certificates and keys. For Java-based applications, your keys and certificates are stored in your Java Keystore, which are often used for encryption, authentication, and serving over HTTPS, thus it’s very important to know how to build and manage it.

> “A Java KeyStore (JKS) is a repository of security certificates – either authorization certificates or public key certificates – plus corresponding private keys, used for instance in SSL encryption.” – Wikipedia

“A Java KeyStore (JKS) is a repository of security certificates – either authorization certificates or public key certificates – plus corresponding private keys, used for instance in SSL encryption.” – Wikipedia

When it comes to managing Java Keystores, Keytool is the utility you are most likely to find. This command is useful to manipulate Java Keystores, and it is included with Java.

> “ Java Keytool is a key and certificate management utility. It allows users to manage their own public/private key pairs and certificates. “ – SSL Shopper

“ Java Keytool is a key and certificate management utility. It allows users to manage their own public/private key pairs and certificates. “ – SSL Shopper

## JKS or PKCS12: which format should you use in 2026?

Since Java 9, PKCS12 is the default keystore type (JEP 229), and recent versions of keytool actively recommend migrating away from the proprietary JKS format. PKCS12 is an industry standard, so the same file can be read by Java, OpenSSL and most web servers and load balancers.

In practice:

- If your application runs on Java 9 or later , you can simply use the .p12 file created in step 2 as your keystore, and skip step 3.
- If a legacy application or third-party product still requires JKS , follow step 3 and keep the -deststoretype JKS flag. Without it, modern keytool versions create a PKCS12 file even if you name it .jks .

Either way, the key point of this guide stays the same: the alias must contain the full certificate chain , not just your domain certificate.

So now, let us go to the guide on how to build a Java Keystore with an alias with the complete certificate chain! Quick hint: the "trick" is in the first step !

## Step by step: how to build a Java Keystore alias with a complete certificate chain

1) First, you need to concatenate all the certificates (your domain's certificate, the intermediate certificate and the root certificate). The order is important.

| cat my_certificate.pem intermediate.pem root.pem > import.pem |
|---|

The order must be: your domain certificate first, then the intermediate certificate(s), and finally the root certificate. Each certificate must keep its -----BEGIN CERTIFICATE----- and -----END CERTIFICATE----- lines.

2) Then you need to convert the key/certificate (chain) pair to pkcs12 format , because certificates in the pem format cannot directly import to a Java Keystore.

| openssl pkcs12 -export -in import.pem -inkey my_key.pem -name my_alias -out my_key_crt_bundle.p12 |
|---|

The -name option defines the alias that will hold the key and the full chain inside the keystore. If you leave it out, OpenSSL creates an alias with no friendly name and keytool will show it as 1 .

Tip for OpenSSL 3: OpenSSL 3 encrypts PKCS12 files with modern algorithms (AES-256) by default. Older Java 8 builds cannot read these files and fail with errors such as "keystore password was incorrect". In that case, update Java or add the -legacy option to the openssl pkcs12 command.

3) And finally, you will have to create the final Java Keystore based on the pkcs12 file created in the previous step.

| keytool -importkeystore -deststorepass my_password -destkeystore my_keystore.jks -deststoretype JKS -srckeystore my_key_crt_bundle.p12 -srcstoretype PKCS12 |
|---|

By listing the content of this Java Keystore, with the following command, you will confirm that there is only one alias with 3 certificates (the certificate chain), instead of 3 aliases (each with its own certificate).

| keytool -list -v -keystore my_keystore.jks |
|---|

In the output, check that your alias shows Certificate chain length: 3 (or the number of certificates in your chain). If it shows 1, the chain was not included and you should review step 1.

This way, when the client application opens a session to your server, it receives the complete certification chain, allowing your domain certificate to be accepted.

## Common errors and how to fix them

- "No certificate matches private key" (OpenSSL, step 2): the first certificate in import.pem is not the one that matches your private key. Make sure your domain certificate comes first, and that you are using the right key file.
- "unable to load certificates" (OpenSSL, step 2): one of the files is not in PEM format, often because it was delivered in DER (binary) format. Convert it with openssl x509 -inform der -in cert.cer -out cert.pem and repeat step 1.
- Chain length is 1 : the certificates were not combined into import.pem , for example because echo was used instead of cat . Repeat step 1.
- "keystore password was incorrect" on an older Java version : see the OpenSSL 3 tip above and use -legacy .
- Clients still show "unable to find valid certification path" : the root certificate may not be trusted by the client. Import it into the client truststore with keytool -importcert .

## Need help managing certificates and Java applications?

Certificate management is just one part of keeping Java applications secure and reliable in production. At Syone, our teams build, modernise and support Java applications for organisations across Europe.

Learn more about our software development services and Java expertise , or contact our team to discuss your project.

Explore our software development services

## Frequently asked questions

An alias is the name of an entry inside a Java Keystore. A private key entry stores the private key together with its certificate chain, and applications use the alias to know which key and certificates to present, for example when serving HTTPS.

If the alias only contains the domain certificate, clients may not be able to link it to a trusted root and will reject the connection. Including the intermediate and root certificates in the same alias ensures the server sends the complete chain during the TLS handshake.

Start with your domain certificate, followed by the intermediate certificate or certificates, and finish with the root certificate. A wrong order is one of the most common reasons why the chain is not recognised.

PKCS12 is the default keystore type since Java 9 and is the recommended format for new projects, as it is an industry standard supported by Java, OpenSSL and most servers. Use JKS only when a legacy application or product explicitly requires it.

Run keytool -list -v -keystore my_keystore.jks and look at your alias. The output should show a certificate chain length equal to the number of certificates you concatenated, usually 3. A length of 1 means only the domain certificate was imported.

### Simplify your infrastructure monitoring with a powerful, cost-effective solution

This exclusive whitepaper reveals how SMBs and public sector organizations can boost visibility, cut costs, and prevent critical failures using Zabbix, the enterprise-grade open-source monitoring platform.
