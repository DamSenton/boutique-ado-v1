from django.http import HttpResponse


class StripeWH_Handler:
    """
    Handle Stripe Webhooks
    """

    def __init__(self, request):
        self.request = request

    def handle_event(self, event):
        """
        Handle a generic/unknown/unexpected webhook event
        """
        return HttpResponse(
            content=f'Unhandled webhook Received: {event["type"]}',
            status=200)

    def handle_payment_intent_succeeded(self, event):
        """
        Handle the payment_intent.succeeded webhook
        """
        intent = event.data.object
        pid = intent.id
        bag = intent.metadata.bag
        save_info = intent.metadata.saveinfo

        billing_details = intent.charges.data[0].billing_details
        shipping_details = intent.shipping_details
        grand_total = round(intent.data.charges[0].amount / 100, 2)

        # Clean data in the shipping details
        for field, value in shipping_details.address.items():
            if value == "":
                shipping_details.address[field] = None

        order_exists = False
        try:
            order = Order.objects.get(
                full_name_iexact=shipping_details.name,
                email_iexact=shipping_details.email,
                phone_number_iexact=shipping_details.phone_number,
                country_iexact=shipping_details.country,
                postcode_iexact=shipping_details.postcode,
                town_or_city_iexact=shipping_details.town_or_city,
                street_address1_iexact=shipping_details.street_address1,
                street_address2_iexact=shipping_details.street_address2,
                county_iexact=shipping_details.state,
                grand_total_iexact=grand_total,
            )
            order_exists = True
            return HttpResponse(
                content=f'Webhook Received: {event["type"]}| SUCCESS: Verified order already exists in the database',
                status=200)
        except Order.DoesNotExist:
            try:
                order = Order.objects.create(
                    full_name=shipping_details.name,
                    email=shipping_details.email,
                    phone_number=shipping_details.phone_number,
                    country=shipping_details.country,
                    postcode=shipping_details.postcode,
                    town_or_city=shipping_details.town_or_city,
                    street_address1=shipping_details.street_address1,
                    street_address2=shipping_details.street_address2,
                    county=shipping_details.state,
                )
                for item_id, item_data in json.loads(bag).items():
                    product = Product.objects.get(id=item_id)
                    if isinstance(item_data, int):
                        order_line_item = OrderLineItem(
                            order=order,
                            product=product,
                            quantity=item_data,
                        )
                        order_line_item.save()
                    else:
                        for size, quantity in item_data['items_by_size'].items():
                            order_line_item = OrderLineItem(
                                order=order,
                                product=product,
                                quantity=quantity,
                                product_size=size,
                            )
                            order_line_item.save()
            except Exception as e:
                if order:
                    order.delete()
                    return HttpResponse(content=f'Webhook Received: {event["type"]} | ERROR: {e}', status=500)

            return HttpResponse(
                content=f'Webhook Received: {event["type"]}',
                status=200)

    def handle_payment_intent_payment_failed(self, event):
        """
        Handle the payment_intent.payment_failed webhook
        """
        return HttpResponse(
            content=f'Webhook Received: {event["type"]}',
            status=200)
